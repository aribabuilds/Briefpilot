"""Deterministic validation for extracted fields (CLAUDE.md §5.2): deadlines
fall on or after the letter date, amounts are non-negative, and legal
references match a curated set of real German statute abbreviations. A failure
never rewrites the value -- it only downgrades confidence and appends a
machine-readable flag (ADR-0005), the same non-negotiable as source-span
linking's confidence cap (D26): an impossible-looking value may still be what
the letter says, so the UI must show it as unproven, never silently correct it
or hide it.

("Dates parse" and "amounts numeric" from CLAUDE.md §5.2 are already enforced
one layer up: `LetterExtraction`'s Pydantic types are `date`/`Decimal`, and the
extraction parser (M9) degrades anything that doesn't parse to `None` before a
`LetterExtraction` is ever constructed. What's left to check here is semantic,
cross-field consistency that no type system enforces on its own.)

Pure functions of an already-parsed LetterExtraction, same discipline as
source_span_linking.py (D25) and OCR normalization (D8): no network, no OCR,
no LLM call, exhaustively unit-testable on its own.
"""

import re
from datetime import date
from decimal import Decimal

from app.schemas.extraction import ExtractedField, LetterExtraction

# Lower than source_span_linking's UNVERIFIED_CONFIDENCE_CAP (0.4): failing a
# deterministic sanity check (a deadline before the letter that sets it, a
# negative fine) is a stronger signal of a likely-wrong value than merely
# "could not be matched back to the OCR text" -- unproven vs. self-contradictory
# are different severities and deserve different ceilings. Placeholder pending
# real-data tuning (M13's decision point), same posture as every other
# threshold in this codebase (M6, D26).
VALIDATION_FAILURE_CONFIDENCE_CAP = 0.2

# Curated, not exhaustive: the statute abbreviations that actually appear
# across BriefPilot's 8 in-scope letter types (CLAUDE.md §1) -- tax (Finanzamt),
# residence (Ausländerbehörde), health insurance (Krankenkasse), fines
# (Bußgeld), broadcast fee (Rundfunkbeitrag), benefits (Jobcenter), and
# rental/utility (BGB). A reference against a code outside this list is flagged
# as unrecognized, not rejected -- it may be a real, rarer citation the
# whitelist hasn't caught up to yet (null-not-guess extends to "don't silently
# drop it either").
_KNOWN_LAW_CODES = frozenset(
    {
        "AO",
        "EStG",
        "UStG",
        "AufenthG",
        "FreizügG/EU",
        "FreizuegG/EU",
        "SGB I",
        "SGB II",
        "SGB III",
        "SGB IV",
        "SGB V",
        "SGB VI",
        "SGB IX",
        "SGB X",
        "SGB XII",
        "StVO",
        "StVG",
        "OWiG",
        "RBStV",
        "BGB",
        "GG",
        "GewO",
        "GKG",
        "VwVfG",
        "VwGO",
    }
)

# Matches "§ 152 AO", "§152a Abs. 2 EStG", "Art. 3 GG" -- captures the trailing
# law-code token to check against _KNOWN_LAW_CODES. Deliberately permissive on
# the numbering (paragraph number, optional letter suffix, optional "Abs. N")
# since only the code identity is being verified here, not the citation's
# internal correctness.
_REFERENCE_PATTERN = re.compile(
    r"^(§+\s?\d+[a-zA-Z]?(\s?(Abs\.?|Absatz)\s?\d+)?|Art\.?\s?\d+)\s+"
    r"(?P<code>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]*(/[A-Z]+)?(\s[IVX]+)?)"
)


def _flag[T](field: ExtractedField[T], issue: str) -> ExtractedField[T]:
    return field.model_copy(
        update={
            "confidence": min(field.confidence, VALIDATION_FAILURE_CONFIDENCE_CAP),
            "validation_issues": [*field.validation_issues, issue],
        }
    )


def is_recognized_legal_reference(reference: str) -> bool:
    match = _REFERENCE_PATTERN.match(reference.strip())
    if match is None:
        return False
    return match.group("code") in _KNOWN_LAW_CODES


def _validate_deadline(
    letter_date: ExtractedField[date], deadline: ExtractedField[date]
) -> ExtractedField[date]:
    if letter_date.value is None or deadline.value is None:
        return deadline
    if deadline.value < letter_date.value:
        return _flag(deadline, "deadline_before_letter_date")
    return deadline


def _validate_amount(amount: ExtractedField[Decimal]) -> ExtractedField[Decimal]:
    if amount.value is None:
        return amount
    if amount.value < 0:
        return _flag(amount, "negative_amount")
    return amount


def _validate_legal_references(
    field: ExtractedField[list[str]],
) -> ExtractedField[list[str]]:
    # An empty list means "confidently found none" (M9/D27) -- nothing to
    # check, and not itself a validation failure.
    if not field.value:
        return field
    if any(not is_recognized_legal_reference(ref) for ref in field.value):
        return _flag(field, "unrecognized_legal_reference")
    return field


def validate_extraction(extraction: LetterExtraction) -> LetterExtraction:
    return extraction.model_copy(
        update={
            "deadline": _validate_deadline(extraction.letter_date, extraction.deadline),
            "amount": _validate_amount(extraction.amount),
            "legal_references": _validate_legal_references(extraction.legal_references),
        }
    )
