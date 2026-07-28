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
from PIL import Image, ImageDraw, ImageFont

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
    image = Image.new("RGB", (1000, 300), "white")
    font = ImageFont.load_default(size=44)
    ImageDraw.Draw(image).text((40, 60), "Finanzamt Muenchen", fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()


def _poll_until_terminal(
    client: TestClient, job_id: str, *, timeout: float = 30.0
) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body: dict[str, object] = client.get(f"/api/v1/jobs/{job_id}").json()
        if body["status"] in (JobStatus.DONE.value, JobStatus.FAILED.value):
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
