"""Unit tests for scoring.py's comparison LOGIC only, using synthetic dicts
written to exercise edge cases -- not real letters, and never treated as an
accuracy measurement. See eval/golden/README.md for what an actual, honest
scorecard requires."""

from collections import Counter

from scoring import (
    FIELDS,
    FieldOutcome,
    aggregate,
    field_accuracy,
    generate_scorecard_markdown,
    score_document,
    score_field,
)

# --- score_field: text fields --------------------------------------------


def test_score_field_correct_null_when_both_missing() -> None:
    assert score_field("sender", None, None) == FieldOutcome.CORRECT_NULL


def test_score_field_hallucinated_when_label_null_but_extracted_has_value() -> None:
    assert score_field("sender", None, "Finanzamt Muenchen") == FieldOutcome.HALLUCINATED


def test_score_field_missed_when_label_has_value_but_extracted_null() -> None:
    assert score_field("sender", "Finanzamt Muenchen", None) == FieldOutcome.MISSED


def test_score_field_correct_when_text_matches_exactly() -> None:
    assert score_field("sender", "Finanzamt Muenchen", "Finanzamt Muenchen") == FieldOutcome.CORRECT


def test_score_field_correct_when_text_differs_only_by_case_and_whitespace() -> None:
    assert (
        score_field("sender", "Finanzamt  Muenchen", "finanzamt muenchen") == FieldOutcome.CORRECT
    )


def test_score_field_wrong_when_text_genuinely_differs() -> None:
    assert score_field("sender", "Finanzamt Muenchen", "Krankenkasse AOK") == FieldOutcome.WRONG


# --- score_field: date fields ---------------------------------------------


def test_score_field_date_is_exact_no_fuzzy_matching() -> None:
    assert score_field("deadline", "2026-03-25", "2026-03-26") == FieldOutcome.WRONG
    assert score_field("deadline", "2026-03-25", "2026-03-25") == FieldOutcome.CORRECT


# --- score_field: amount ----------------------------------------------------


def test_score_field_amount_matches_across_int_float_str() -> None:
    assert score_field("amount", 184.50, 184.5) == FieldOutcome.CORRECT
    assert score_field("amount", 184.50, "184.50") == FieldOutcome.CORRECT


def test_score_field_amount_rounds_to_cents() -> None:
    assert score_field("amount", 184.50, 184.4999) == FieldOutcome.CORRECT


def test_score_field_amount_wrong_when_genuinely_different() -> None:
    assert score_field("amount", 184.50, 250.00) == FieldOutcome.WRONG


# --- score_field: list fields ------------------------------------------------


def test_score_field_list_ignores_order() -> None:
    assert (
        score_field("legal_references", ["§ 152 AO", "§ 41 SGB II"], ["§ 41 SGB II", "§ 152 AO"])
        == FieldOutcome.CORRECT
    )


def test_score_field_list_empty_list_and_null_are_equivalent() -> None:
    assert score_field("legal_references", [], None) == FieldOutcome.CORRECT_NULL
    assert score_field("legal_references", None, []) == FieldOutcome.CORRECT_NULL


def test_score_field_list_wrong_when_items_differ() -> None:
    outcome = score_field("required_actions", ["Pay by deadline"], ["Submit missing receipts"])
    assert outcome == FieldOutcome.WRONG


def test_score_field_list_hallucinated_when_label_has_none_but_extraction_lists_items() -> None:
    outcome = score_field("legal_references", [], ["§ 152 AO"])
    assert outcome == FieldOutcome.HALLUCINATED


# --- score_document -----------------------------------------------------------


def test_score_document_scores_every_field() -> None:
    label = {
        "sender": "Finanzamt Muenchen",
        "doc_type": "finanzamt",
        "letter_date": "2026-03-04",
        "deadline": "2026-03-25",
        "amount": 184.50,
        "legal_references": ["§ 152 AO"],
        "required_actions": ["Pay by deadline"],
    }
    extracted = dict(label)  # a "perfect" extraction
    result = score_document(label, extracted)
    assert set(result.keys()) == set(FIELDS)
    assert all(outcome == FieldOutcome.CORRECT for outcome in result.values())


def test_score_document_handles_a_mix_of_outcomes() -> None:
    label = {
        "sender": "Finanzamt Muenchen",
        "doc_type": "finanzamt",
        "letter_date": "2026-03-04",
        "deadline": "2026-03-25",
        "amount": 184.50,
        "legal_references": ["§ 152 AO"],
        "required_actions": None,
    }
    extracted = {
        "sender": "Finanzamt Muenchen",  # correct
        "doc_type": "krankenkasse",  # wrong
        "letter_date": "2026-03-04",  # correct
        "deadline": None,  # missed
        "amount": 184.50,  # correct
        "legal_references": ["§ 152 AO"],  # correct
        "required_actions": ["Pay by deadline"],  # hallucinated
    }
    result = score_document(label, extracted)
    assert result["sender"] == FieldOutcome.CORRECT
    assert result["doc_type"] == FieldOutcome.WRONG
    assert result["deadline"] == FieldOutcome.MISSED
    assert result["required_actions"] == FieldOutcome.HALLUCINATED


# --- aggregate + field_accuracy -----------------------------------------------


def test_aggregate_and_field_accuracy_across_multiple_documents() -> None:
    doc_scores = [
        {"sender": FieldOutcome.CORRECT, "amount": FieldOutcome.WRONG},
        {"sender": FieldOutcome.CORRECT, "amount": FieldOutcome.CORRECT},
        {"sender": FieldOutcome.WRONG, "amount": FieldOutcome.HALLUCINATED},
    ]
    tallies = aggregate(doc_scores)
    assert tallies["sender"] == Counter({FieldOutcome.CORRECT: 2, FieldOutcome.WRONG: 1})
    assert field_accuracy(tallies["sender"]) == 2 / 3
    assert field_accuracy(tallies["amount"]) == 1 / 3


def test_field_accuracy_counts_correct_null_as_correct() -> None:
    tally: Counter[FieldOutcome] = Counter(
        {FieldOutcome.CORRECT: 1, FieldOutcome.CORRECT_NULL: 1, FieldOutcome.WRONG: 2}
    )
    assert field_accuracy(tally) == 0.5


def test_field_accuracy_is_none_for_an_empty_tally() -> None:
    assert field_accuracy(Counter()) is None


# --- generate_scorecard_markdown ----------------------------------------------


def test_generate_scorecard_markdown_is_honest_about_zero_documents() -> None:
    markdown = generate_scorecard_markdown({}, document_count=0)
    assert "0 golden letters" in markdown
    assert "not an accuracy measurement" in markdown
    assert "|" not in markdown  # no fabricated table


def test_generate_scorecard_markdown_renders_a_table_when_documents_exist() -> None:
    tallies = aggregate([{"sender": FieldOutcome.CORRECT}])
    markdown = generate_scorecard_markdown(tallies, document_count=1)
    assert "| sender |" in markdown
    assert "100%" in markdown
    assert "Hallucinated" in markdown
