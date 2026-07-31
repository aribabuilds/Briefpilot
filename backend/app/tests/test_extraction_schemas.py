from datetime import date
from decimal import Decimal

from app.schemas.extraction import ExtractedField, LetterExtraction, SourceSpan
from app.schemas.ocr import BBox


def test_extracted_field_holds_a_null_value_without_a_source_span() -> None:
    field: ExtractedField[str] = ExtractedField(value=None, confidence=0.0)
    assert field.value is None
    assert field.source_span is None


def test_extracted_field_is_generic_over_different_value_types() -> None:
    text: ExtractedField[str] = ExtractedField(value="Finanzamt", confidence=0.9)
    amount: ExtractedField[Decimal] = ExtractedField(value=Decimal("184.50"), confidence=0.8)
    day: ExtractedField[date] = ExtractedField(value=date(2026, 3, 1), confidence=0.7)
    refs: ExtractedField[list[str]] = ExtractedField(value=["§ 152 AO"], confidence=0.6)

    assert text.value == "Finanzamt"
    assert amount.value == Decimal("184.50")
    assert day.value == date(2026, 3, 1)
    assert refs.value == ["§ 152 AO"]


def test_extracted_field_can_carry_a_source_span() -> None:
    span = SourceSpan(page=0, bboxes=[BBox(x=0.1, y=0.1, width=0.2, height=0.05)])
    field: ExtractedField[str] = ExtractedField(value="Finanzamt", confidence=0.9, source_span=span)
    assert field.source_span is not None
    assert field.source_span.page == 0
    assert len(field.source_span.bboxes) == 1


def test_decimal_amount_serializes_to_json_string_not_number() -> None:
    # Documented consequence of using Decimal for money: Pydantic serializes
    # it as a string to preserve precision. The frontend must not parse it as
    # a JS number.
    field: ExtractedField[Decimal] = ExtractedField(value=Decimal("184.50"), confidence=0.9)
    assert '"value":"184.50"' in field.model_dump_json()


def test_letter_extraction_holds_all_six_fields_independently() -> None:
    extraction = LetterExtraction(
        sender=ExtractedField(value="Finanzamt Muenchen", confidence=0.95),
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.9),
        deadline=ExtractedField(value=date(2026, 3, 31), confidence=0.92),
        amount=ExtractedField(value=Decimal("250.00"), confidence=0.9),
        legal_references=ExtractedField(value=["§ 152 AO"], confidence=0.85),
        required_actions=ExtractedField(value=["Pay by the deadline"], confidence=0.8),
    )
    assert extraction.sender.value == "Finanzamt Muenchen"
    assert extraction.deadline.value == date(2026, 3, 31)
    assert extraction.amount.value == Decimal("250.00")


def test_letter_extraction_allows_every_field_to_be_null_independently() -> None:
    # A letter with no discernible deadline or amount is a real, valid state --
    # not every field needs a value for the extraction to be meaningful.
    extraction = LetterExtraction(
        sender=ExtractedField(value="Unknown sender", confidence=0.3),
        letter_date=ExtractedField(value=None, confidence=0.0),
        deadline=ExtractedField(value=None, confidence=0.0),
        amount=ExtractedField(value=None, confidence=0.0),
        legal_references=ExtractedField(value=[], confidence=0.5),
        required_actions=ExtractedField(value=[], confidence=0.5),
    )
    assert extraction.deadline.value is None
    assert extraction.amount.value is None
    # Empty list is a real, confident answer ("we looked, found none") --
    # distinct from None ("we don't know").
    assert extraction.legal_references.value == []
