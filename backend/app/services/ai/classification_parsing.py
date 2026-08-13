"""Parses an LLM's raw text response into a ClassificationResult.

Shared across every AIService adapter so classification behaves identically
regardless of provider (same reasoning as the OCR normalization split in
tesseract_service.py: a pure function is trivially unit-tested with no network
call, and there is exactly one place that decides what "malformed" means).

Never raises: a response that isn't valid JSON, is missing a field, or names
an unrecognized doc_type degrades to OTHER at confidence 0.0 rather than
crashing the job or guessing a specific type. This is the same null-not-guess
instinct as the OCR quality gate (M6) and the extraction contract's
{value, confidence, source_span} wrapper coming at M9 — an honest "we don't
know" beats a plausible-looking wrong answer.
"""

from app.schemas.classification import ClassificationResult, DocumentType
from app.services.ai.json_parsing import extract_json_value

_UNKNOWN_RESULT = ClassificationResult(doc_type=DocumentType.OTHER, confidence=0.0)


def parse_classification_response(raw_text: str) -> ClassificationResult:
    data = extract_json_value(raw_text)
    try:
        doc_type = DocumentType(str(data["doc_type"]).strip().lower())  # type: ignore[index]
        confidence = max(0.0, min(1.0, float(data["confidence"])))  # type: ignore[index]
    except (KeyError, ValueError, TypeError):
        return _UNKNOWN_RESULT
    return ClassificationResult(doc_type=doc_type, confidence=confidence)
