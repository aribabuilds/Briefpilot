import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

import structlog

from app.config.settings import get_settings
from app.repositories.document_store import DocumentStore, InMemoryDocumentStore
from app.repositories.job_repository import InMemoryJobRepository, JobRepository
from app.schemas.ai import (
    DocumentExplanationRequest,
    DocumentExplanationResult,
    DocumentExtractionRequest,
)
from app.schemas.classification import ClassificationRequest, ClassificationResult
from app.schemas.explanation import ExplanationResult
from app.schemas.extraction import ExtractedField, LetterExtraction
from app.schemas.job import Job, JobResult, JobStatus
from app.schemas.ocr import OcrDocument
from app.services.advice_linter import find_advice_phrases
from app.services.ai import get_ai_service
from app.services.document_pipeline import build_document
from app.services.ocr import TesseractOcrService
from app.services.quality import assess_quality
from app.services.readability import assess_readability
from app.services.retention import purge_expired
from app.services.source_span_linking import link_source_spans
from app.services.validators import validate_extraction

logger = structlog.get_logger(__name__)

# The pipeline reduced to what the job layer needs: bytes + content type -> document.
DocumentRunner = Callable[[bytes, str], OcrDocument]
# Likewise reduced for classification, extraction, and explanation: text (and,
# for explanation, the already-extracted fields) in, a result out. JobService
# never imports AIService or knows an LLM is involved — same seam as
# DocumentRunner.
ClassifierRunner = Callable[[str], ClassificationResult]
ExtractorRunner = Callable[[str], LetterExtraction]
ExplainerRunner = Callable[[str, LetterExtraction], DocumentExplanationResult]


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
        explainer: ExplainerRunner | None = None,
        document_store: DocumentStore | None = None,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._executor = executor
        self._min_mean_confidence = min_mean_confidence
        self._min_word_count = min_word_count
        self._classifier = classifier
        self._extractor = extractor
        self._explainer = explainer
        self._document_store = document_store

    def create_job(self, *, filename: str, content: bytes, content_type: str) -> Job:
        job = Job(
            id=uuid4().hex,
            status=JobStatus.PROCESSING,
            filename=filename,
            created_at=datetime.now(UTC),
        )
        self._repository.add(job)
        # Stored immediately, independent of OCR completing -- the viewer
        # (M18) can render the original scan even while the job is still
        # processing, and this is the only place the raw bytes are ever
        # available (the pipeline consumes them and moves on).
        if self._document_store is not None:
            self._document_store.put(job.id, content=content, content_type=content_type)
        self._executor.submit(self._process, job.id, filename, content, content_type)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._repository.get(job_id)

    def get_document(self, job_id: str) -> tuple[bytes, str] | None:
        if self._document_store is None:
            return None
        return self._document_store.get(job_id)

    def delete_job(self, job_id: str) -> bool:
        """One-click delete (M22). Removes both the job record and its raw
        document bytes -- the two stores this app persists a user's data in
        -- and reports whether there was anything to delete, so the API layer
        can answer 204 vs. 404 without a second lookup."""
        existed = self._repository.delete(job_id)
        if self._document_store is not None:
            self._document_store.delete(job_id)
        return existed

    def purge_expired(self, *, now: datetime, max_age: timedelta) -> list[str]:
        """24h auto-purge (M22). Thin wrapper so the background sweep task in
        main.py never reaches into this service's private repository/store
        attributes."""
        return purge_expired(self._repository, self._document_store, now=now, max_age=max_age)

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
                validated = validate_extraction(linked)
                result = result.model_copy(update={"extraction": validated})
            except Exception:  # noqa: BLE001 - best-effort; never fail the job over this
                logger.warning("extraction_failed", job_id=job_id, exc_info=True)

        # Explanation is likewise best-effort and independent of the other two
        # -- grounded on document.text plus whatever extraction produced
        # (falling back to an all-null extraction if extraction itself
        # failed or is unconfigured, still valid grounding input per
        # CLAUDE.md §1.2). Readability and the advice-phrase linter run here,
        # against the model's actual output, not inside the AI adapter --
        # same split as source-span linking/validation for extraction.
        if self._explainer is not None:
            try:
                grounding = result.extraction or _empty_extraction()
                raw = self._explainer(document.text, grounding)
                readability = assess_readability(raw.explanation)
                explanation = ExplanationResult(
                    text=raw.explanation,
                    word_count=readability.word_count,
                    flesch_reading_ease=readability.flesch_reading_ease,
                    exceeds_word_limit=readability.exceeds_word_limit,
                    below_readability_target=readability.below_readability_target,
                    advice_phrases_found=find_advice_phrases(raw.explanation),
                )
                result = result.model_copy(update={"explanation": explanation})
            except Exception:  # noqa: BLE001 - best-effort; never fail the job over this
                logger.warning("explanation_failed", job_id=job_id, exc_info=True)

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


def _empty_extraction() -> LetterExtraction:
    return LetterExtraction(
        sender=ExtractedField(value=None, confidence=0.0),
        letter_date=ExtractedField(value=None, confidence=0.0),
        deadline=ExtractedField(value=None, confidence=0.0),
        amount=ExtractedField(value=None, confidence=0.0),
        legal_references=ExtractedField(value=None, confidence=0.0),
        required_actions=ExtractedField(value=None, confidence=0.0),
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


def _explain(text: str, extraction: LetterExtraction) -> DocumentExplanationResult:
    # Same lazy get_ai_service() call as _classify/_extract.
    ai_service = get_ai_service()
    request = DocumentExplanationRequest(content=text, extraction=extraction)
    return asyncio.run(ai_service.explain_document(request))


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
        explainer=_explain,
        document_store=InMemoryDocumentStore(),
    )
