"""End-to-end: a real PDF upload runs the real pipeline (rasterize -> preprocess
-> Tesseract) through the actual JobService and background worker, and the polled
job returns the extracted text. Needs the Tesseract binary, so it is skipped
where absent but runs — and must not silently skip — in CI (LEARNING.md D2).

Deliberately overrides get_job_service with classifier=None, extractor=None
(real OCR, no AI calls) rather than using the raw app + get_job_service()
default. This test predates classification (M8) and extraction (M9/M10),
which get_job_service()'s factory now wires in unconditionally whenever an
AI_PROVIDER/API key happens to be configured -- invisible for most of this
project's life because no key existed, but once one is added locally this
test would otherwise make real, slow, occasionally-503-flaky network calls
to score something (OCR pipeline mechanics) that has nothing to do with
classification or extraction. Same "override, don't depend on ambient
config" discipline as test_jobs.py and test_extraction_e2e.py.
"""

import io
import os
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytesseract
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.config.settings import get_settings
from app.main import app
from app.repositories.job_repository import InMemoryJobRepository
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
    # Needs >= min_word_count (5, see Settings) so the real run clears the M6
    # quality gate and reaches DONE rather than LOW_QUALITY.
    image = Image.new("RGB", (1000, 320), "white")
    font = ImageFont.load_default(size=40)
    draw = ImageDraw.Draw(image)
    lines = ["Finanzamt Muenchen", "Steuerbescheid 2026", "Bitte zahlen Sie den Betrag"]
    for i, line in enumerate(lines):
        draw.text((40, 30 + i * 90), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()


def _unreadable_photo_pdf() -> bytes:
    # A deliberately bad photo: tiny, low-contrast text, heavily blurred.
    # Gaussian blur destroys the sharp edges OCR needs regardless of contrast,
    # so CLAHE's local-contrast preprocessing (M4) cannot recover legibility --
    # this should genuinely be near-zero words at low confidence, not merely
    # "hard". Sprint-1's DoD ("quality gate triggers on a deliberately bad
    # photo") has never actually been proven against real Tesseract until now.
    image = Image.new("RGB", (700, 220), "white")
    font = ImageFont.load_default(size=8)
    draw = ImageDraw.Draw(image)
    draw.text(
        (20, 20), "kaum lesbarer verwaschener Text auf diesem Foto", fill=(232, 232, 232), font=font
    )
    image = image.filter(ImageFilter.GaussianBlur(radius=10))
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()


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


def _real_ocr_only_service() -> JobService:
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
        classifier=None,
        extractor=None,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = _real_ocr_only_service()
    app.dependency_overrides[get_job_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_job_service, None)


def test_upload_runs_real_ocr_and_returns_text(client: TestClient) -> None:
    created = client.post(
        "/api/v1/jobs",
        files={"file": ("letter.pdf", _letter_pdf(), "application/pdf")},
    )
    assert created.status_code == 201

    body = _poll_until_terminal(client, created.json()["id"])
    assert body["status"] == JobStatus.DONE.value, body
    result = body["result"]
    assert isinstance(result, dict)
    assert "finanzamt" in str(result["text"]).lower()
    assert int(result["word_count"]) >= 1


def test_deliberately_bad_photo_is_marked_low_quality(client: TestClient) -> None:
    # Sprint-1's own Definition of Done: "quality gate triggers on a
    # deliberately bad photo" -- proven here against the real pipeline, not a
    # synthetic confidence dict (that's test_quality.py's job).
    created = client.post(
        "/api/v1/jobs",
        files={"file": ("bad-photo.pdf", _unreadable_photo_pdf(), "application/pdf")},
    )
    assert created.status_code == 201

    body = _poll_until_terminal(client, created.json()["id"])
    assert body["status"] == JobStatus.LOW_QUALITY.value, body
