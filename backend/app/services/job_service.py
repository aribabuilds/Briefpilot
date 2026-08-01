import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

import structlog

from app.config.settings import get_settings
from app.repositories.job_repository import InMemoryJobRepository, JobRepository
from app.schemas.ai import DocumentExtractionRequest
from app.schemas.classification import ClassificationRequest, ClassificationResult
from app.schemas.extraction import LetterExtraction
from app.schemas.job import Job, JobResult, JobStatus
from app.schemas.ocr import OcrDocument
from app.services.ai import get_ai_service
from app.services.document_pipeline import build_document
from app.services.ocr import TesseractOcrService
from app.services.quality import assess_quality
from app.services.source_span_linking import link_source_spans

logger = structlog.get_logger(__name__)

# The pipeline reduced to what the job layer needs: bytes + content type -> document.
DocumentRunner = Callable[[bytes, str], OcrDocument]
# Likewise reduced for classification and extraction: text in, a result out.
# JobService never imports AIService or knows an LLM is involved — same seam
# as DocumentRunner.
ClassifierRunner = Callable[[str], ClassificationResult]
ExtractorRunner = Callable[[str], LetterExtraction]


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
        self,
        repository: JobRepository,
        runner: DocumentRunner,
        executor: Executor,
        *,
        min_mean_confidence: float,
        min_word_count: int,
        classifier: ClassifierRunner | None = None,
        extractor: ExtractorRunner | None = None,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._executor = executor
        self._min_mean_confidence = min_mean_confidence
        self._min_word_count = min_word_count
        self._classifier = classifier
        self._extractor = extractor

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

        assessment = assess_quality(
            document,
            min_mean_confidence=self._min_mean_confidence,
            min_word_count=self._min_word_count,
        )
        result = _summarize(filename, document)
        if not assessment.passed:
            logger.info("job_low_quality", job_id=job_id, reason=assessment.reason)
            self._update(job_id, status=JobStatus.LOW_QUALITY, result=result)
            return

        # Classification is best-effort and must never fail the job: a missing
        # API key, a network error, or a provider outage all degrade to
        # doc_type=None (null-not-guess) rather than a FAILED job over a
        # capability that isn't OCR's responsibility.
        if self._classifier is not None:
            try:
                classification = self._classifier(document.text)
                result = result.model_copy(
                    update={
                        "doc_type": classification.doc_type,
                        "doc_type_confidence": classification.confidence,
                    }
                )
            except Exception:  # noqa: BLE001 - best-effort; never fail the job over this
                logger.warning("classification_failed", job_id=job_id, exc_info=True)

        # Extraction is likewise best-effort and independent of classification:
        # a letter can fail to classify but still have extractable fields, or
        # vice versa. Source-span linking runs against the real OcrDocument
        # already in scope here, filling in what the AI call alone can't
        # honestly claim (M9: adapters only see flattened text, never bboxes).
        if self._extractor is not None:
            try:
                extraction = self._extractor(document.text)
                linked = link_source_spans(extraction, document)
                result = result.model_copy(update={"extraction": linked})
            except Exception:  # noqa: BLE001 - best-effort; never fail the job over this
                logger.warning("extraction_failed", job_id=job_id, exc_info=True)

        self._update(job_id, status=JobStatus.DONE, result=result)

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


def _classify(text: str) -> ClassificationResult:
    # get_ai_service() is only called here, per job, not at startup -- a
    # missing GEMINI_API_KEY (or any other provider misconfiguration) surfaces
    # as a RuntimeError caught by JobService's best-effort classification
    # block, not as a crash on app boot or on every unrelated upload.
    ai_service = get_ai_service()
    return asyncio.run(ai_service.classify_document(ClassificationRequest(content=text)))


def _extract(text: str) -> LetterExtraction:
    # Same lazy get_ai_service() call as _classify -- deferred to per-job, not
    # app startup.
    ai_service = get_ai_service()
    return asyncio.run(ai_service.extract_document(DocumentExtractionRequest(content=text)))


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
    return JobService(
        InMemoryJobRepository(),
        runner,
        executor,
        min_mean_confidence=settings.min_mean_confidence,
        min_word_count=settings.min_word_count,
        classifier=_classify,
        extractor=_extract,
    )
