"""OCR quality gate.

The philosophical sibling of the M5 silent-failure fix (LEARNING.md D12): an OCR
run can *succeed* mechanically yet produce output too unreliable to show — a
blurry or badly-lit photo yields a few low-confidence words. Handing that to the
user as if it were the letter's content is worse than admitting we couldn't read
it. This gate turns "technically done" into an honest pass/retake decision.

Pure and deterministic, so it is exhaustively unit-testable without the Tesseract
binary. Thresholds live in settings and are meant to be tuned against real bad
photos as the golden set grows.
"""

from dataclasses import dataclass

from app.schemas.ocr import OcrDocument


@dataclass(frozen=True)
class QualityAssessment:
    passed: bool
    mean_confidence: float
    word_count: int
    reason: str | None = None


def assess_quality(
    document: OcrDocument,
    *,
    min_mean_confidence: float,
    min_word_count: int,
) -> QualityAssessment:
    words = document.words
    word_count = len(words)

    if word_count == 0:
        return QualityAssessment(
            passed=False, mean_confidence=0.0, word_count=0, reason="no text detected"
        )

    mean_confidence = sum(word.confidence for word in words) / word_count

    if word_count < min_word_count:
        return QualityAssessment(
            passed=False,
            mean_confidence=mean_confidence,
            word_count=word_count,
            reason=f"only {word_count} words detected (min {min_word_count})",
        )

    if mean_confidence < min_mean_confidence:
        return QualityAssessment(
            passed=False,
            mean_confidence=mean_confidence,
            word_count=word_count,
            reason=f"mean confidence {mean_confidence:.2f} below {min_mean_confidence:.2f}",
        )

    return QualityAssessment(
        passed=True, mean_confidence=mean_confidence, word_count=word_count, reason=None
    )
