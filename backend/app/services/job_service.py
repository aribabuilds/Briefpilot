from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

import structlog

from app.config.settings import get_settings
from app.repositories.job_repository import InMemoryJobRepository, JobRepository
from app.schemas.job import Job, JobResult, JobStatus
from app.schemas.ocr import OcrDocument
from app.services.document_pipeline import build_document
from app.services.ocr import TesseractOcrService

logger = structlog.get_logger(__name__)

# The pipeline reduced to what the job layer needs: bytes + content type -> document.
DocumentRunner = Callable[[bytes, str], OcrDocument]


class Executor(Protocol):
    """Minimal submit surface. Satisfied by ThreadPoolExecutor in production and
    by a synchronous stand-in in tests, which makes job completion deterministic."""

    def submit(self, fn: Callable[..., object], /, *args: object) -> object: ...


class JobService:
    """Owns the job lifecycle. Upload creates a PROCESSING job and hands the real
    work to an executor off the request path; the worker updates the job to DONE
    (with the extracted document) or FAILED (with an error) when it finishes.

    This replaces M2's lazily-evaluated stub completion: real OCR must run exactly
    once, in the background, not be recomputed on every poll.
    """

    def __init__(
        self, repository: JobRepository, runner: DocumentRunner, executor: Executor
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._executor = executor

    def create_job(self, *, filename: str, content: bytes, content_type: str) -> Job:
        job = Job(
            id=uuid4().hex,
            status=JobStatus.PROCESSING,
            filename=filename,
            created_at=datetime.now(UTC),
        )
        self._repository.add(job)
        self._executor.submit(self._process, job.id, filename, content, content_type)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._repository.get(job_id)

    def _process(self, job_id: str, filename: str, content: bytes, content_type: str) -> None:
        try:
            document = self._runner(content, content_type)
        except Exception as exc:  # noqa: BLE001 - the worker must never crash silently
            logger.exception("job_processing_failed", job_id=job_id)
            self._update(job_id, status=JobStatus.FAILED, error=str(exc))
            return
        self._update(job_id, status=JobStatus.DONE, result=_summarize(filename, document))

    def _update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result: JobResult | None = None,
        error: str | None = None,
    ) -> None:
        job = self._repository.get(job_id)
        if job is None:  # pragma: no cover - defensive; the job was just created
            return
        self._repository.update(
            job.model_copy(update={"status": status, "result": result, "error": error})
        )


def _summarize(filename: str, document: OcrDocument) -> JobResult:
    words = document.words
    mean_confidence = sum(word.confidence for word in words) / len(words) if words else 0.0
    return JobResult(
        filename=filename,
        page_count=len(document.pages),
        word_count=len(words),
        mean_confidence=mean_confidence,
        text=document.text,
    )


@lru_cache
def get_job_service() -> JobService:
    settings = get_settings()
    ocr = TesseractOcrService(language=settings.ocr_language, timeout=settings.ocr_timeout_seconds)

    def runner(content: bytes, content_type: str) -> OcrDocument:
        return build_document(
            content,
            content_type,
            ocr=ocr,
            max_pages=settings.max_document_pages,
            render_scale=settings.ocr_render_scale,
            preprocess_enabled=settings.preprocess_enabled,
            deskew_max_angle=settings.deskew_max_angle,
            max_dimension=settings.preprocess_max_dimension,
        )

    executor = ThreadPoolExecutor(
        max_workers=settings.ocr_worker_threads,
        thread_name_prefix="ocr",
    )
    return JobService(InMemoryJobRepository(), runner, executor)
