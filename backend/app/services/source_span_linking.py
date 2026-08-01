"""Links an already-extracted LetterExtraction back to the OCR words it came
from — the provenance CLAUDE.md §5.3 requires ("every extracted field links
back to OCR word spans").

Deliberately separate from both the AI adapters (which only see flattened
text, never OcrWords — ADR-0004) and from OCR itself: a pure function of
(LetterExtraction, OcrDocument), unit-tested with neither a live LLM nor a
real Tesseract call, same discipline as OCR normalization (D8) and
classification/extraction parsing (D19, M9).

An LLM's extracted value rarely matches OCR's literal tokens verbatim (a
`date` object vs. whatever German format the letter actually used, a Decimal
vs. a comma-formatted amount with a currency symbol attached). The match is
split in two: candidate generators produce plausible surface forms for a
value, and find_source_span does one simple thing — exact matching of a
contiguous OCR word window against those candidates.

When no candidate matches, the field's value is kept (it may still be
correct) but its confidence is capped: an ungrounded value must not look as
trustworthy as a verified one, or the source-highlight overlay's entire trust
story (a extracted value being provably tied to the original scan) is
undermined for the one case it exists to catch. This mirrors CLAUDE.md
§5.2's validator rule — failures downgrade confidence and flag, never
silently pass. The cap (0.4) is a placeholder pending real-data tuning once
golden letters exist (M13's decision point), same as the OCR quality
thresholds (M6).
"""

import re
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal

from app.schemas.extraction import ExtractedField, LetterExtraction, SourceSpan
from app.schemas.ocr import OcrDocument, OcrWord

# Confidence ceiling for a field whose value could not be matched back to any
# OCR word span. Not zero: the value may still be right, just unverified.
UNVERIFIED_CONFIDENCE_CAP = 0.4

_MAX_WINDOW_WORDS = 6

_GERMAN_MONTHS = {
    1: "januar",
    2: "februar",
    3: "märz",
    4: "april",
    5: "mai",
    6: "juni",
    7: "juli",
    8: "august",
    9: "september",
    10: "oktober",
    11: "november",
    12: "dezember",
}


def date_candidates(value: date) -> list[str]:
    day, month, year = value.day, value.month, value.year
    two_digit_year = year % 100
    month_name = _GERMAN_MONTHS[month]
    return [
        f"{day:02d}.{month:02d}.{year}",  # 01.03.2026
        f"{day}.{month}.{year}",  # 1.3.2026
        f"{day:02d}.{month:02d}.{two_digit_year:02d}",  # 01.03.26
        f"{day}. {month_name} {year}",  # 1. März 2026
        f"{day:02d}. {month_name} {year}",  # 01. März 2026
    ]


def amount_candidates(value: Decimal) -> list[str]:
    cents = value.quantize(Decimal("0.01"))
    period_form = str(cents)  # "250.00"
    comma_form = period_form.replace(".", ",")  # "250,00"

    candidates = {
        period_form,
        comma_form,
        f"{comma_form} EUR",
        f"{comma_form}EUR",
        f"{comma_form} €",
        f"{comma_form}€",
        f"{period_form} EUR",
        f"{period_form}€",
    }

    if cents == cents.to_integral_value():
        whole = str(int(cents))
        candidates.update({whole, f"{whole} EUR", f"{whole}€", f"{whole},-", f"{whole},- EUR"})

    return sorted(candidates)


def find_source_span(
    candidates: Sequence[str], words: Sequence[OcrWord], *, max_window: int = _MAX_WINDOW_WORDS
) -> SourceSpan | None:
    normalized_candidates = {_normalize(c) for c in candidates if c.strip()}
    if not normalized_candidates:
        return None

    words_by_page: dict[int, list[OcrWord]] = {}
    for word in words:
        words_by_page.setdefault(word.page, []).append(word)

    for page in sorted(words_by_page):
        page_words = words_by_page[page]
        for window_size in range(1, max_window + 1):
            for start in range(0, len(page_words) - window_size + 1):
                window = page_words[start : start + window_size]
                joined = " ".join(word.text for word in window)
                if _normalize(joined) in normalized_candidates:
                    return SourceSpan(page=page, bboxes=[word.bbox for word in window])
    return None


def _normalize(text: str) -> str:
    return re.sub(r"[.,;:]+$", "", text.strip().lower())


def link_source_spans(extraction: LetterExtraction, document: OcrDocument) -> LetterExtraction:
    words = document.words
    return LetterExtraction(
        sender=_link_scalar(extraction.sender, lambda v: [v], words),
        letter_date=_link_scalar(extraction.letter_date, date_candidates, words),
        deadline=_link_scalar(extraction.deadline, date_candidates, words),
        amount=_link_scalar(extraction.amount, amount_candidates, words),
        legal_references=_link_list(extraction.legal_references, words),
        required_actions=_link_list(extraction.required_actions, words),
    )


def _link_scalar[
    T
](
    field: ExtractedField[T],
    candidates_fn: Callable[[T], list[str]],
    words: Sequence[OcrWord],
) -> ExtractedField[T]:
    if field.value is None:
        return field
    span = find_source_span(candidates_fn(field.value), words)
    if span is None:
        return field.model_copy(
            update={"confidence": min(field.confidence, UNVERIFIED_CONFIDENCE_CAP)}
        )
    return field.model_copy(update={"source_span": span})


def _link_list(
    field: ExtractedField[list[str]], words: Sequence[OcrWord]
) -> ExtractedField[list[str]]:
    # A list field gets one SourceSpan for the whole field, not per item, so a
    # multi-item value can only ever point at its first item's location -- a
    # known, documented simplification rather than a schema change mid-freeze.
    if not field.value:
        return field
    span = find_source_span([field.value[0]], words)
    if span is None:
        return field.model_copy(
            update={"confidence": min(field.confidence, UNVERIFIED_CONFIDENCE_CAP)}
        )
    return field.model_copy(update={"source_span": span})
