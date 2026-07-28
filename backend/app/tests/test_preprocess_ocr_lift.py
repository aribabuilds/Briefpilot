"""The measurable-lift claim: preprocessing raises OCR confidence on a skewed
photo. Needs the real Tesseract binary, so it is skipped where Tesseract is
absent but runs — and must not silently skip — in CI (same guard as the OCR
integration test; see LEARNING.md D2).
"""

import os

import pytesseract
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr.tesseract_service import TesseractOcrService
from app.services.preprocess import preprocess_page


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


def _skewed_page() -> Image.Image:
    page = Image.new("RGB", (900, 320), "white")
    font = ImageFont.load_default(size=38)
    draw = ImageDraw.Draw(page)
    for i, line in enumerate(["Finanzamt Muenchen", "Bescheid ueber 250 Euro", "Bitte zahlen Sie"]):
        draw.text((40, 30 + i * 80), line, fill="black", font=font)
    # 12 deg: skewed enough that raw OCR clearly degrades, but inside the deskew
    # correction window (the guard treats >14 deg as unreliable and skips).
    return page.rotate(12.0, expand=True, fillcolor="white", resample=Image.Resampling.BICUBIC)


def _mean_confidence(image: Image.Image) -> float:
    page = TesseractOcrService().extract_page(image, page=0)
    if not page.words:
        return 0.0
    return sum(word.confidence for word in page.words) / len(page.words)


def test_preprocessing_improves_mean_confidence_on_skewed_page() -> None:
    skewed = _skewed_page()
    raw_confidence = _mean_confidence(skewed)
    preprocessed_confidence = _mean_confidence(preprocess_page(skewed))

    assert preprocessed_confidence > raw_confidence, (
        f"expected preprocessing to lift confidence, "
        f"got raw={raw_confidence:.3f} preprocessed={preprocessed_confidence:.3f}"
    )
