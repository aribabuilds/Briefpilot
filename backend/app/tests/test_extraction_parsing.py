from datetime import date
from decimal import Decimal

from app.services.ai.extraction_parsing import parse_letter_extraction

_CLEAN_JSON = """
{
  "sender": {"value": "Finanzamt Musterstadt", "confidence": 0.95},
  "letter_date": {"value": "2026-03-01", "confidence": 0.9},
  "deadline": {"value": "2026-03-31", "confidence": 0.92},
  "amount": {"value": "250.00", "confidence": 0.9},
  "legal_references": {"value": ["Paragraph 152 AO"], "confidence": 0.85},
  "required_actions": {"value": ["Pay by the deadline"], "confidence": 0.8}
}
"""


def test_parses_clean_json_into_typed_values() -> None:
    result = parse_letter_extraction(_CLEAN_JSON)
    assert result.sender.value == "Finanzamt Musterstadt"
    assert result.letter_date.value == date(2026, 3, 1)
    assert result.deadline.value == date(2026, 3, 31)
    assert result.amount.value == Decimal("250.00")
    assert result.legal_references.value == ["Paragraph 152 AO"]
    assert result.required_actions.value == ["Pay by the deadline"]
    assert result.sender.confidence == 0.95


def test_source_span_is_always_none_source_linking_is_m10() -> None:
    result = parse_letter_extraction(_CLEAN_JSON)
    assert result.sender.source_span is None
    assert result.amount.source_span is None


def test_strips_markdown_code_fences() -> None:
    raw = f"```json\n{_CLEAN_JSON}\n```"
    result = parse_letter_extraction(raw)
    assert result.sender.value == "Finanzamt Musterstadt"


def test_completely_invalid_json_yields_all_null_fields_zero_confidence() -> None:
    result = parse_letter_extraction("not json at all")
    assert result.sender.value is None
    assert result.sender.confidence == 0.0
    assert result.amount.value is None
    assert result.legal_references.value is None


def test_null_value_forces_confidence_to_zero_even_if_llm_claimed_otherwise() -> None:
    raw = '{"sender": {"value": null, "confidence": 0.9}}'
    result = parse_letter_extraction(raw)
    assert result.sender.value is None
    assert result.sender.confidence == 0.0


def test_empty_list_is_a_real_value_not_a_null() -> None:
    raw = '{"legal_references": {"value": [], "confidence": 0.7}}'
    result = parse_letter_extraction(raw)
    assert result.legal_references.value == []
    assert result.legal_references.confidence == 0.7


def test_missing_list_field_is_null_not_empty_list() -> None:
    result = parse_letter_extraction("{}")
    assert result.legal_references.value is None
    assert result.legal_references.confidence == 0.0


def test_malformed_date_string_falls_back_to_null() -> None:
    raw = '{"deadline": {"value": "not-a-date", "confidence": 0.8}}'
    result = parse_letter_extraction(raw)
    assert result.deadline.value is None
    assert result.deadline.confidence == 0.0


def test_malformed_amount_falls_back_to_null() -> None:
    raw = '{"amount": {"value": "a lot of money", "confidence": 0.8}}'
    result = parse_letter_extraction(raw)
    assert result.amount.value is None
    assert result.amount.confidence == 0.0


def test_amount_accepts_plain_numeric_value_not_just_string() -> None:
    raw = '{"amount": {"value": 184.5, "confidence": 0.8}}'
    result = parse_letter_extraction(raw)
    assert result.amount.value == Decimal("184.5")


def test_non_dict_field_entry_falls_back_to_null() -> None:
    raw = '{"sender": "not the expected shape"}'
    result = parse_letter_extraction(raw)
    assert result.sender.value is None
    assert result.sender.confidence == 0.0


def test_confidence_clamped_to_unit_interval() -> None:
    raw = '{"sender": {"value": "X", "confidence": 5.0}}'
    result = parse_letter_extraction(raw)
    assert result.sender.confidence == 1.0


def test_non_numeric_confidence_falls_back_to_zero() -> None:
    raw = '{"sender": {"value": "X", "confidence": "very sure"}}'
    result = parse_letter_extraction(raw)
    # A real value with an unparseable confidence keeps the value but at 0.0 --
    # never invent a confidence number that was never actually given.
    assert result.sender.value == "X"
    assert result.sender.confidence == 0.0


def test_string_list_items_are_stripped_and_blanks_dropped() -> None:
    raw = '{"required_actions": {"value": ["  Pay now  ", "", "  "], "confidence": 0.6}}'
    result = parse_letter_extraction(raw)
    assert result.required_actions.value == ["Pay now"]


def test_empty_string_input_yields_all_null_fields() -> None:
    result = parse_letter_extraction("")
    assert result.sender.value is None
    assert result.letter_date.value is None
