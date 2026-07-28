"""Real Tesseract integration — the binary is the thing under test here.

Skipped automatically where Tesseract is not installed (e.g. the owner's
Windows machine); runs for real in CI, which installs the engine. This is the
seam where "does our normalization match what Tesseract actually emits" is
verified against the live tool rather than a synthetic dict.
"""

import pytesseract
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr.tesseract_service import TesseractOcrService


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # pragma: no cover - environment-dependent
        return False


pytestmark = pytest.mark.skipif(
    not _tesseract_available(),
    reason="Tesseract binary not installed (runs in CI)",
)


def _image_with_text(text: str) -> Image.Image:
    image = Image.new("RGB", (900, 200), "white")
    font = ImageFont.load_default(size=48)
    ImageDraw.Draw(image).text((30, 60), text, fill="black", font=font)
    return image


def test_extract_page_reads_clear_text() -> None:
    service = TesseractOcrService()
    page = service.extract_page(_image_with_text("Finanzamt Muenchen"), page=0)

    joined = " ".join(word.text for word in page.words).lower()
    assert "finanzamt" in joined
    assert page.words, "expected at least one recognized word"


def test_extract_page_reports_geometry_and_confidence_in_range() -> None:
    service = TesseractOcrService()
    page = service.extract_page(_image_with_text("Bescheid"), page=2)

    assert page.page == 2
    for word in page.words:
        assert word.page == 2
        assert 0.0 <= word.confidence <= 1.0
        assert 0.0 <= word.bbox.x <= 1.0
        assert 0.0 <= word.bbox.y <= 1.0
        assert 0.0 < word.bbox.width <= 1.0
        assert 0.0 < word.bbox.height <= 1.0
