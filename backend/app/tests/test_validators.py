from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.schemas.extraction import ExtractedField, LetterExtraction
from app.services.validators import (
    VALIDATION_FAILURE_CONFIDENCE_CAP,
    is_recognized_legal_reference,
    validate_extraction,
)


def _base_extraction(**overrides: ExtractedField[Any]) -> LetterExtraction:
    defaults: dict[str, ExtractedField[Any]] = {
        "sender": ExtractedField(value=None, confidence=0.0),
        "letter_date": ExtractedField(value=None, confidence=0.0),
        "deadline": ExtractedField(value=None, confidence=0.0),
        "amount": ExtractedField(value=None, confidence=0.0),
        "legal_references": ExtractedField(value=None, confidence=0.0),
        "required_actions": ExtractedField(value=None, confidence=0.0),
    }
    defaults.update(overrides)
    return LetterExtraction(**defaults)


# --- is_recognized_legal_reference -------------------------------------------


@pytest.mark.parametrize(
    "reference",
    [
        "§ 152 AO",
        "§152 AO",
        "§ 152a AO",
        "§ 152 Abs. 2 AO",
        "§ 41 SGB II",
        "Art. 3 GG",
        "Art 3 GG",
    ],
)
def test_is_recognized_legal_reference_accepts_known_forms(reference: str) -> None:
    assert is_recognized_legal_reference(reference)


@pytest.mark.parametrize(
    "reference",
    [
        "§ 152 XYZ",  # not a real code
        "just some text",
        "",
        "§ 152",  # no code at all
    ],
)
def test_is_recognized_legal_reference_rejects_unknown_forms(reference: str) -> None:
    assert not is_recognized_legal_reference(reference)


# --- validate_extraction: deadline vs letter_date -----------------------------


def test_validate_extraction_flags_deadline_before_letter_date() -> None:
    extraction = _base_extraction(
        letter_date=ExtractedField(value=date(2026, 3, 10), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
    )
    validated = validate_extraction(extraction)
    assert validated.deadline.value == date(2026, 3, 1)  # value untouched
    assert validated.deadline.confidence == VALIDATION_FAILURE_CONFIDENCE_CAP
    assert "deadline_before_letter_date" in validated.deadline.validation_issues


def test_validate_extraction_allows_deadline_on_the_letter_date() -> None:
    same_day = date(2026, 3, 10)
    extraction = _base_extraction(
        letter_date=ExtractedField(value=same_day, confidence=0.9),
        deadline=ExtractedField(value=same_day, confidence=0.9),
    )
    validated = validate_extraction(extraction)
    assert validated.deadline.validation_issues == []
    assert validated.deadline.confidence == 0.9


def test_validate_extraction_allows_deadline_after_letter_date() -> None:
    extraction = _base_extraction(
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 31), confidence=0.9),
    )
    validated = validate_extraction(extraction)
    assert validated.deadline.validation_issues == []
    assert validated.deadline.confidence == 0.9


def test_validate_extraction_skips_deadline_check_when_letter_date_missing() -> None:
    extraction = _base_extraction(
        deadline=ExtractedField(value=date(2026, 3, 31), confidence=0.9),
    )
    validated = validate_extraction(extraction)
    assert validated.deadline.validation_issues == []


def test_validate_extraction_never_raises_the_cap_above_original_confidence() -> None:
    extraction = _base_extraction(
        letter_date=ExtractedField(value=date(2026, 3, 10), confidence=0.05),
        deadline=ExtractedField(value=date(2026, 3, 1), confidence=0.05),
    )
    validated = validate_extraction(extraction)
    assert validated.deadline.confidence == 0.05


# --- validate_extraction: amount ----------------------------------------------


def test_validate_extraction_flags_negative_amount() -> None:
    extraction = _base_extraction(amount=ExtractedField(value=Decimal("-50.00"), confidence=0.8))
    validated = validate_extraction(extraction)
    assert validated.amount.value == Decimal("-50.00")
    assert validated.amount.confidence == VALIDATION_FAILURE_CONFIDENCE_CAP
    assert "negative_amount" in validated.amount.validation_issues


def test_validate_extraction_allows_zero_amount() -> None:
    extraction = _base_extraction(amount=ExtractedField(value=Decimal("0.00"), confidence=0.8))
    validated = validate_extraction(extraction)
    assert validated.amount.validation_issues == []


def test_validate_extraction_allows_positive_amount() -> None:
    extraction = _base_extraction(amount=ExtractedField(value=Decimal("250.00"), confidence=0.8))
    validated = validate_extraction(extraction)
    assert validated.amount.validation_issues == []
    assert validated.amount.confidence == 0.8


def test_validate_extraction_skips_amount_check_when_null() -> None:
    extraction = _base_extraction()
    validated = validate_extraction(extraction)
    assert validated.amount.validation_issues == []


# --- validate_extraction: legal_references ------------------------------------


def test_validate_extraction_flags_unrecognized_legal_reference() -> None:
    extraction = _base_extraction(
        legal_references=ExtractedField(value=["§ 999 NOTREAL"], confidence=0.7)
    )
    validated = validate_extraction(extraction)
    assert validated.legal_references.value == ["§ 999 NOTREAL"]
    assert validated.legal_references.confidence == VALIDATION_FAILURE_CONFIDENCE_CAP
    assert "unrecognized_legal_reference" in validated.legal_references.validation_issues


def test_validate_extraction_allows_recognized_legal_reference() -> None:
    extraction = _base_extraction(
        legal_references=ExtractedField(value=["§ 152 AO"], confidence=0.7)
    )
    validated = validate_extraction(extraction)
    assert validated.legal_references.validation_issues == []
    assert validated.legal_references.confidence == 0.7


def test_validate_extraction_flags_whole_field_if_any_reference_is_unrecognized() -> None:
    extraction = _base_extraction(
        legal_references=ExtractedField(value=["§ 152 AO", "§ 1 MADEUP"], confidence=0.7)
    )
    validated = validate_extraction(extraction)
    assert "unrecognized_legal_reference" in validated.legal_references.validation_issues


def test_validate_extraction_empty_legal_references_list_is_not_a_failure() -> None:
    extraction = _base_extraction(legal_references=ExtractedField(value=[], confidence=0.6))
    validated = validate_extraction(extraction)
    assert validated.legal_references.value == []
    assert validated.legal_references.validation_issues == []
    assert validated.legal_references.confidence == 0.6


# --- validate_extraction: fields untouched by validators are unaffected ------


def test_validate_extraction_leaves_sender_and_required_actions_untouched() -> None:
    extraction = _base_extraction(
        sender=ExtractedField(value="Finanzamt", confidence=0.9),
        required_actions=ExtractedField(value=["Pay by deadline"], confidence=0.85),
    )
    validated = validate_extraction(extraction)
    assert validated.sender == extraction.sender
    assert validated.required_actions == extraction.required_actions


def test_validate_extraction_can_flag_multiple_fields_independently() -> None:
    extraction = _base_extraction(
        letter_date=ExtractedField(value=date(2026, 3, 10), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        amount=ExtractedField(value=Decimal("-1.00"), confidence=0.8),
    )
    validated = validate_extraction(extraction)
    assert "deadline_before_letter_date" in validated.deadline.validation_issues
    assert "negative_amount" in validated.amount.validation_issues
