"""Parses an LLM's raw JSON text response into a LetterExtraction.

Shared across every AIService adapter — same reasoning as
classification_parsing.py (D19): one place owns what "malformed" means,
unit-tested with no network call.

Source-span linking (matching a value back to the specific OCR words that
support it) is deliberately NOT done here — that requires the OcrDocument the
value came from, and per the plan's own Day-9/Day-10 split, wiring that up is
M10's job. Every field's source_span is None for now, which is consistent
with ExtractedField's own contract (None exactly when there's nothing to
point to — here, we simply haven't looked yet).

Never raises: malformed JSON, a missing field, or a value that fails to
coerce to its real type (a bad date string, a non-numeric amount) degrades
that field to null at confidence 0.0 rather than crashing the caller or
guessing — the same null-not-guess instinct as OCR quality (M6) and
classification (M8).
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from app.schemas.extraction import ExtractedField, LetterExtraction
from app.services.ai.json_parsing import extract_json_value


def parse_letter_extraction(raw_text: str) -> LetterExtraction:
    data = extract_json_value(raw_text)
    if not isinstance(data, dict):
        data = {}

    return LetterExtraction(
        sender=_field(data.get("sender"), _coerce_str),
        letter_date=_field(data.get("letter_date"), _coerce_date),
        deadline=_field(data.get("deadline"), _coerce_date),
        amount=_field(data.get("amount"), _coerce_decimal),
        legal_references=_field(data.get("legal_references"), _coerce_str_list),
        required_actions=_field(data.get("required_actions"), _coerce_str_list),
    )


def _field[T](raw: object, coerce: Callable[[object], T | None]) -> ExtractedField[T]:
    if not isinstance(raw, dict):
        return ExtractedField(value=None, confidence=0.0)
    value = coerce(raw.get("value"))
    confidence = _coerce_confidence(raw.get("confidence"))
    # No value means nothing was actually claimed -- don't let a stray
    # confidence number survive a null (a list's [] is a real value, not this).
    if value is None:
        confidence = 0.0
    return ExtractedField(value=value, confidence=confidence)


def _coerce_confidence(raw: object) -> float:
    try:
        return max(0.0, min(1.0, float(raw)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _coerce_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _coerce_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _coerce_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _coerce_str_list(value: object) -> list[str] | None:
    # A real (possibly empty) list means "we looked and found this many";
    # anything else (missing, wrong type) means "not evaluated".
    if not isinstance(value, list):
        return None
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
