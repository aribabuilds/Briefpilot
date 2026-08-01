"""End-to-end: real Tesseract OCR feeds real source-span linking.

No Gemini key exists yet (PROGRESS.md), so the AI call itself is faked here —
same as the JobService wiring tests. What this test proves that those can't:
that link_source_spans, wired into the real JobService, finds real bboxes in
real OCR word output, not just synthetic OcrWord fixtures. Needs the
Tesseract binary; skipped where absent but required (never silently skipped)
in CI (LEARNING.md D2).
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
    # Larger font and more generous spacing than every earlier OCR test in
    # this project (M5-M9 only ever matched plain words) -- this is the
    # first test requiring digit-level OCR fidelity for dates and amounts, a
    # genuinely harder recognition task than a whole word.
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


def _fake_extractor(text: str) -> LetterExtraction:
    # Deliberately matches _letter_pdf()'s rendered text, so real OCR + real
    # source-span linking can be verified end to end without a live LLM.
    return LetterExtraction(
        sender=ExtractedField(value="Finanzamt Muenchen", confidence=0.9),
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 31), confidence=0.9),
        amount=ExtractedField(value=Decimal("250.00"), confidence=0.9),
        legal_references=ExtractedField(value=[], confidence=0.5),
        required_actions=ExtractedField(value=[], confidence=0.5),
    )


def _real_ocr_service_with_fake_extractor() -> JobService:
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
        extractor=_fake_extractor,
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


def test_source_span_linking_finds_real_bboxes_in_real_ocr_output() -> None:
    app.dependency_overrides[get_job_service] = _real_ocr_service_with_fake_extractor
    try:
        client = TestClient(app)
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("letter.pdf", _letter_pdf(), "application/pdf")},
        )
        assert created.status_code == 201

        body = _poll_until_terminal(client, created.json()["id"])
        assert body["status"] == JobStatus.DONE.value, body
        extraction = body["result"]["extraction"]  # type: ignore[index]
        assert extraction is not None

        # Sender is plain text -- the same reliable pattern every OCR test in
        # this project (M5-M9) has matched on. It must link.
        assert extraction["sender"]["source_span"] is not None
        assert extraction["sender"]["confidence"] == pytest.approx(0.9)

        # Dates/amounts need digit-level OCR fidelity for the first time in
        # this project -- a genuinely harder task on a synthetic render than
        # matching a whole word. Requiring at least one to link is still a
        # real proof that numeric candidate matching works against real OCR
        # output (not just a synthetic OcrWord fixture), without over-betting
        # on perfect character recognition of every digit in a CI runner.
        digit_fields = ["letter_date", "deadline", "amount"]
        linked = [f for f in digit_fields if extraction[f]["source_span"] is not None]
        assert linked, f"expected at least one of {digit_fields} to link; got {extraction}"
    finally:
        app.dependency_overrides.pop(get_job_service, None)
