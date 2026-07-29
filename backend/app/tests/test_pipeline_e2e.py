"""End-to-end: a real PDF upload runs the real pipeline (rasterize -> preprocess
-> Tesseract) through the actual JobService and background worker, and the polled
job returns the extracted text. Needs the Tesseract binary, so it is skipped
where absent but runs — and must not silently skip — in CI (LEARNING.md D2).
"""

import io
import os
import time

import pytesseract
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.main import app
from app.schemas.job import JobStatus


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


def test_upload_runs_real_ocr_and_returns_text() -> None:
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
    assert "finanzamt" in str(result["text"]).lower()
    assert int(result["word_count"]) >= 1


def test_deliberately_bad_photo_is_marked_low_quality() -> None:
    # Sprint-1's own Definition of Done: "quality gate triggers on a
    # deliberately bad photo" -- proven here against the real pipeline, not a
    # synthetic confidence dict (that's test_quality.py's job).
    client = TestClient(app)
    created = client.post(
        "/api/v1/jobs",
        files={"file": ("bad-photo.pdf", _unreadable_photo_pdf(), "application/pdf")},
    )
    assert created.status_code == 201

    body = _poll_until_terminal(client, created.json()["id"])
    assert body["status"] == JobStatus.LOW_QUALITY.value, body
