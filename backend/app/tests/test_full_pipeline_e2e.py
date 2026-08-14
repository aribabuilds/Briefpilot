"""End-to-end: the WHOLE JobService pipeline in one real run -- real Tesseract
OCR feeding classification, extraction (+ source-span linking + validation),
and explanation (+ readability + advice-linter), all in a single job. This is
the "full journey keeps working" regression test M20 asks for: every earlier
e2e test in this suite covers a slice (test_pipeline_e2e.py: OCR alone;
test_extraction_e2e.py: OCR + extraction only) -- none of them prove
classification and explanation stay correctly wired in alongside extraction
in the same job, which is exactly the kind of thing a future refactor could
silently break without a test that actually exercises all four together.

Classification/extraction/explanation are injected fakes (deterministic, free
-- same discipline as every other e2e test here: no live LLM call, so CI
never depends on external quota). Needs the Tesseract binary; skipped where
absent but required (never silently skipped) in CI.
"""

import io
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytesseract
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.config.settings import get_settings
from app.main import app
from app.repositories.job_repository import InMemoryJobRepository
from app.schemas.ai import DocumentExplanationResult
from app.schemas.classification import ClassificationResult, DocumentType
from app.schemas.extraction import ExtractedField, LetterExtraction
from app.schemas.job import JobStatus
from app.schemas.ocr import OcrDocument
from app.services.document_pipeline import build_document
from app.services.job_service import JobService, get_job_service
from app.services.ocr import TesseractOcrService


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # pragma: no cover - environment-dependent
        return False


_IN_CI = os.getenv("CI") == "true"

pytestmark = pytest.mark.skipif(
    not _tesseract_available() and not _IN_CI,
    reason="Tesseract binary not installed (runs, and is required, in CI)",
)


def _letter_pdf() -> bytes:
    image = Image.new("RGB", (1200, 420), "white")
    font = ImageFont.load_default(size=56)
    draw = ImageDraw.Draw(image)
    lines = [
        "Finanzamt Muenchen",
        "Steuerbescheid vom 01.03.2026",
        "Betrag 250,00 EUR faellig 31.03.2026",
    ]
    for i, line in enumerate(lines):
        draw.text((40, 20 + i * 120), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()


def _fake_classifier(text: str) -> ClassificationResult:
    return ClassificationResult(doc_type=DocumentType.FINANZAMT, confidence=0.95)


def _fake_extractor(text: str) -> LetterExtraction:
    # Matches _letter_pdf()'s rendered text -- real source-span linking needs
    # real overlap with the real OCR output.
    return LetterExtraction(
        sender=ExtractedField(value="Finanzamt Muenchen", confidence=0.9),
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 31), confidence=0.9),
        amount=ExtractedField(value=Decimal("250.00"), confidence=0.9),
        legal_references=ExtractedField(value=[], confidence=0.5),
        required_actions=ExtractedField(value=[], confidence=0.5),
    )


def _fake_explainer(text: str, extraction: LetterExtraction) -> DocumentExplanationResult:
    return DocumentExplanationResult(
        explanation="This letter is a tax bill from the Finanzamt. It asks for 250 EUR by March 31."
    )


def _full_pipeline_service() -> JobService:
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

    return JobService(
        InMemoryJobRepository(),
        runner,
        ThreadPoolExecutor(max_workers=settings.ocr_worker_threads, thread_name_prefix="ocr-test"),
        min_mean_confidence=settings.min_mean_confidence,
        min_word_count=settings.min_word_count,
        classifier=_fake_classifier,
        extractor=_fake_extractor,
        explainer=_fake_explainer,
    )


_TERMINAL_STATUSES = frozenset(
    {JobStatus.DONE.value, JobStatus.LOW_QUALITY.value, JobStatus.FAILED.value}
)


def _poll_until_terminal(
    client: TestClient, job_id: str, *, timeout: float = 30.0
) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body: dict[str, object] = client.get(f"/api/v1/jobs/{job_id}").json()
        if body["status"] in _TERMINAL_STATUSES:
            return body
        time.sleep(0.25)
    raise AssertionError("job did not finish within the timeout")


def test_the_whole_pipeline_stays_correctly_wired_together() -> None:
    # Construct ONCE and close over that same instance -- see LEARNING.md's
    # M10 post-merge fix for exactly what goes wrong (a 404 on the very next
    # GET) if the dependency override assigns the factory function instead.
    service = _full_pipeline_service()
    app.dependency_overrides[get_job_service] = lambda: service
    try:
        client = TestClient(app)
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("letter.pdf", _letter_pdf(), "application/pdf")},
        )
        assert created.status_code == 201

        body = _poll_until_terminal(client, created.json()["id"])
        assert body["status"] == JobStatus.DONE.value, body
        result = body["result"]
        assert isinstance(result, dict)

        # OCR really ran.
        assert "finanzamt" in str(result["text"]).lower()
        assert int(result["word_count"]) >= 1

        # Classification stayed wired in alongside extraction and explanation.
        assert result["doc_type"] == DocumentType.FINANZAMT.value
        assert result["doc_type_confidence"] == pytest.approx(0.95)

        # Extraction + source-span linking + validation all ran against the
        # SAME real OcrDocument the OCR step produced.
        extraction = result["extraction"]
        assert isinstance(extraction, dict)
        assert extraction["sender"]["value"] == "Finanzamt Muenchen"
        assert extraction["sender"]["source_span"] is not None  # actually found in the OCR text
        assert extraction["amount"]["value"] == "250.00"

        # Explanation ran, grounded on that same extraction, with its
        # readability + advice-linter checks computed.
        explanation = result["explanation"]
        assert isinstance(explanation, dict)
        assert "Finanzamt" in explanation["text"]
        assert explanation["word_count"] > 0
        assert explanation["advice_phrases_found"] == []
    finally:
        app.dependency_overrides.pop(get_job_service, None)
