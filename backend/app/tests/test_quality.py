import pytest

from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.quality import assess_quality


def _doc(*confidences: float) -> OcrDocument:
    words = [
        OcrWord(text="w", page=0, bbox=BBox(x=0.1, y=0.1, width=0.1, height=0.1), confidence=c)
        for c in confidences
    ]
    return OcrDocument(pages=[OcrPage(page=0, width=100, height=100, words=words)])


def _kwargs() -> dict[str, float | int]:
    return {"min_mean_confidence": 0.5, "min_word_count": 5}


def test_empty_document_fails_with_no_text_reason() -> None:
    result = assess_quality(OcrDocument(pages=[]), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is False
    assert result.word_count == 0
    assert result.reason == "no text detected"


def test_too_few_words_fails_even_with_high_confidence() -> None:
    result = assess_quality(_doc(0.99, 0.99, 0.99), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is False
    assert "words" in (result.reason or "")


def test_low_mean_confidence_fails() -> None:
    result = assess_quality(_doc(0.2, 0.2, 0.2, 0.2, 0.2, 0.2), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is False
    assert "confidence" in (result.reason or "")


def test_healthy_document_passes() -> None:
    result = assess_quality(_doc(0.8, 0.8, 0.9, 0.7, 0.9, 0.85), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is True
    assert result.reason is None
    assert result.word_count == 6
    assert result.mean_confidence == pytest.approx(0.825)


def test_confidence_exactly_at_threshold_passes() -> None:
    # Boundary: mean == threshold is acceptable (the gate rejects *below*).
    result = assess_quality(_doc(0.5, 0.5, 0.5, 0.5, 0.5), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is True


def test_word_count_exactly_at_minimum_passes() -> None:
    result = assess_quality(_doc(0.9, 0.9, 0.9, 0.9, 0.9), **_kwargs())  # type: ignore[arg-type]
    assert result.passed is True
