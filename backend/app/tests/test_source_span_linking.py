from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.schemas.extraction import ExtractedField, LetterExtraction
from app.schemas.ocr import BBox, OcrDocument, OcrPage, OcrWord
from app.services.source_span_linking import (
    UNVERIFIED_CONFIDENCE_CAP,
    amount_candidates,
    date_candidates,
    find_source_span,
    link_source_spans,
)


def _word(text: str, *, page: int = 0, index: int = 0) -> OcrWord:
    return OcrWord(
        text=text,
        page=page,
        bbox=BBox(x=0.05 * index, y=0.1, width=0.04, height=0.02),
        confidence=0.9,
    )


# --- date_candidates --------------------------------------------------------


def test_date_candidates_include_numeric_and_written_forms() -> None:
    candidates = date_candidates(date(2026, 3, 1))
    assert "01.03.2026" in candidates
    assert "1.3.2026" in candidates
    assert "01.03.26" in candidates
    assert "1. märz 2026" in candidates
    assert "01. märz 2026" in candidates


# --- amount_candidates -------------------------------------------------------


def test_amount_candidates_cover_comma_and_period_decimal_forms() -> None:
    candidates = amount_candidates(Decimal("250.00"))
    assert "250,00" in candidates
    assert "250.00" in candidates
    assert "250,00 EUR" in candidates
    assert "250,00€" in candidates


def test_amount_candidates_add_whole_number_forms_when_no_cents() -> None:
    candidates = amount_candidates(Decimal("250.00"))
    assert "250" in candidates
    assert "250,-" in candidates


def test_amount_candidates_omit_whole_number_forms_when_cents_present() -> None:
    candidates = amount_candidates(Decimal("184.50"))
    assert "184" not in candidates
    assert "184,50" in candidates


# --- find_source_span --------------------------------------------------------


def test_find_source_span_matches_single_word() -> None:
    words = [_word("Finanzamt", index=0), _word("01.03.2026", index=1)]
    span = find_source_span(["01.03.2026"], words)
    assert span is not None
    assert span.page == 0
    assert len(span.bboxes) == 1


def test_find_source_span_matches_multi_word_span() -> None:
    words = [_word("Finanzamt", index=0), _word("Musterstadt", index=1), _word("GmbH", index=2)]
    span = find_source_span(["Finanzamt Musterstadt"], words)
    assert span is not None
    assert len(span.bboxes) == 2


def test_find_source_span_is_case_insensitive() -> None:
    words = [_word("FINANZAMT", index=0)]
    assert find_source_span(["finanzamt"], words) is not None


def test_find_source_span_strips_trailing_punctuation() -> None:
    words = [_word("31.03.2026.", index=0)]  # OCR often keeps sentence-final punctuation
    assert find_source_span(["31.03.2026"], words) is not None


def test_find_source_span_does_not_cross_page_boundaries() -> None:
    words = [_word("Finanzamt", page=0, index=0), _word("Musterstadt", page=1, index=0)]
    assert find_source_span(["Finanzamt Musterstadt"], words) is None


def test_find_source_span_returns_none_when_nothing_matches() -> None:
    words = [_word("Krankenkasse", index=0)]
    assert find_source_span(["Finanzamt"], words) is None


def test_find_source_span_returns_none_for_empty_candidates() -> None:
    words = [_word("Finanzamt", index=0)]
    assert find_source_span([], words) is None


def test_find_source_span_matches_any_of_several_candidates() -> None:
    words = [_word("250,00", index=0)]
    span = find_source_span(["250.00", "250,00", "250"], words)
    assert span is not None


# --- link_source_spans (full field wiring + confidence cap) ------------------


def _document(words: list[OcrWord]) -> OcrDocument:
    return OcrDocument(pages=[OcrPage(page=0, width=1000, height=500, words=words)])


def _base_extraction(**overrides: ExtractedField[Any]) -> LetterExtraction:
    # Any: the dict genuinely mixes ExtractedField[str/date/Decimal/list[str]]
    # instances; LetterExtraction's own constructor is what actually enforces
    # each field's real type.
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


def test_link_source_spans_fills_in_span_for_matched_scalar_field() -> None:
    words = [_word("Finanzamt", index=0), _word("Musterstadt", index=1)]
    extraction = _base_extraction(
        sender=ExtractedField(value="Finanzamt Musterstadt", confidence=0.9)
    )
    linked = link_source_spans(extraction, _document(words))
    assert linked.sender.source_span is not None
    assert linked.sender.confidence == 0.9  # unchanged: it was verified


def test_link_source_spans_caps_confidence_when_value_unlinkable() -> None:
    words = [_word("Krankenkasse", index=0)]
    extraction = _base_extraction(sender=ExtractedField(value="Finanzamt", confidence=0.9))
    linked = link_source_spans(extraction, _document(words))
    assert linked.sender.source_span is None
    assert linked.sender.confidence == UNVERIFIED_CONFIDENCE_CAP


def test_link_source_spans_never_raises_the_cap_above_original_confidence() -> None:
    # A field the model was already unsure about should not look MORE
    # confident just because linking failed.
    words = [_word("Krankenkasse", index=0)]
    extraction = _base_extraction(sender=ExtractedField(value="Finanzamt", confidence=0.1))
    linked = link_source_spans(extraction, _document(words))
    assert linked.sender.confidence == 0.1


def test_link_source_spans_leaves_null_fields_untouched() -> None:
    extraction = _base_extraction()  # everything None
    linked = link_source_spans(extraction, _document([]))
    assert linked.sender.value is None
    assert linked.sender.source_span is None
    assert linked.sender.confidence == 0.0


def test_link_source_spans_links_date_fields_via_candidates() -> None:
    words = [_word("01.03.2026", index=0)]
    extraction = _base_extraction(
        letter_date=ExtractedField(value=date(2026, 3, 1), confidence=0.85)
    )
    linked = link_source_spans(extraction, _document(words))
    assert linked.letter_date.source_span is not None


def test_link_source_spans_links_amount_fields_via_candidates() -> None:
    words = [_word("250,00", index=0), _word("EUR", index=1)]
    extraction = _base_extraction(amount=ExtractedField(value=Decimal("250.00"), confidence=0.8))
    linked = link_source_spans(extraction, _document(words))
    assert linked.amount.source_span is not None


def test_link_source_spans_links_list_field_to_its_first_item() -> None:
    words = [_word("Paragraph", index=0), _word("152", index=1), _word("AO", index=2)]
    extraction = _base_extraction(
        legal_references=ExtractedField(value=["Paragraph 152 AO"], confidence=0.7)
    )
    linked = link_source_spans(extraction, _document(words))
    assert linked.legal_references.source_span is not None


def test_link_source_spans_empty_list_value_is_left_alone() -> None:
    # An empty list means "confidently found none" (M9) -- there is nothing to
    # link, and it should not be penalized as unverified.
    extraction = _base_extraction(legal_references=ExtractedField(value=[], confidence=0.6))
    linked = link_source_spans(extraction, _document([]))
    assert linked.legal_references.value == []
    assert linked.legal_references.confidence == 0.6
    assert linked.legal_references.source_span is None


@pytest.mark.parametrize("field_name", ["sender", "letter_date", "deadline", "amount"])
def test_link_source_spans_preserves_the_original_value(field_name: str) -> None:
    words = [_word("irrelevant", index=0)]
    value_by_field = {
        "sender": "Finanzamt",
        "letter_date": date(2026, 1, 1),
        "deadline": date(2026, 1, 1),
        "amount": Decimal("10.00"),
    }
    extraction = _base_extraction(
        **{field_name: ExtractedField(value=value_by_field[field_name], confidence=0.5)}
    )
    linked = link_source_spans(extraction, _document(words))
    assert getattr(linked, field_name).value == value_by_field[field_name]
