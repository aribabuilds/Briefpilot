"""Scores a pipeline's extraction against hand-labeled ground truth
(eval/golden/documents/<id>/label.json). CLAUDE.md §5.5 names the eval suite
"a feature," not a side script: this module is the part of it that decides
what "correct" even means, so it gets the same discipline as the pipeline's
own pure logic (source_span_linking.py, validators.py) -- zero I/O, zero
network, zero dependency on Pydantic or any backend type, exhaustively unit-
tested on its own with synthetic dicts that test the comparison LOGIC, not a
claim about real-world accuracy (that claim only means something once real
golden letters exist -- see eval/golden/README.md).

Deliberately operates on plain JSON-compatible dicts (str / float / list[str] /
None), the exact shape both label.json and LetterExtraction.model_dump(mode="json")
produce, rather than importing backend.app schemas -- eval/ has no dependency
on backend/ being installed just to run the comparison logic.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

# The 6 LetterExtraction fields (ADR-0004) plus doc_type, which comes from
# classification (M8), not extraction, but is labeled and scored alongside
# them since a wrong doc_type is just as real a failure to a user.
FIELDS: tuple[str, ...] = (
    "sender",
    "doc_type",
    "letter_date",
    "deadline",
    "amount",
    "legal_references",
    "required_actions",
)


class FieldOutcome(StrEnum):
    """Five outcomes, not a pass/fail boolean (ADR-0006): collapsing these
    into one accuracy number would hide the one failure mode this whole
    project exists to prevent -- HALLUCINATED (the pipeline claimed a value
    the letter doesn't have) is a categorically worse failure than MISSED
    (the pipeline said null when a human found a real value), and a single
    "wrong" bucket can't tell the two apart.
    """

    CORRECT = "correct"  # both non-null and match
    CORRECT_NULL = "correct_null"  # both null/empty -- a true negative
    MISSED = "missed"  # label has a value, extraction said null
    WRONG = "wrong"  # both non-null, but they disagree
    HALLUCINATED = "hallucinated"  # label is null, extraction invented a value


def _norm_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().casefold().split())
    return text or None


def _norm_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _norm_amount(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _norm_list(value: Any) -> tuple[str, ...] | None:
    # An empty list and a missing/null value are treated as the same "found
    # nothing" state here -- label.json and LetterExtraction both use them
    # interchangeably for "no legal references on this letter" (M9/D27), so
    # scoring must not punish whichever spelling either side happened to use.
    if not value:
        return None
    normalized = tuple(sorted(t for t in (_norm_text(v) for v in value) if t))
    return normalized or None


_NORMALIZERS: dict[str, Any] = {
    "sender": _norm_text,
    "doc_type": _norm_text,
    "letter_date": _norm_date,
    "deadline": _norm_date,
    "amount": _norm_amount,
    "legal_references": _norm_list,
    "required_actions": _norm_list,
}


def score_field(field: str, expected: Any, actual: Any) -> FieldOutcome:
    normalize = _NORMALIZERS[field]
    norm_expected = normalize(expected)
    norm_actual = normalize(actual)
    if norm_expected is None and norm_actual is None:
        return FieldOutcome.CORRECT_NULL
    if norm_expected is None:
        return FieldOutcome.HALLUCINATED
    if norm_actual is None:
        return FieldOutcome.MISSED
    return FieldOutcome.CORRECT if norm_expected == norm_actual else FieldOutcome.WRONG


def score_document(
    label: Mapping[str, Any], extracted: Mapping[str, Any]
) -> dict[str, FieldOutcome]:
    return {field: score_field(field, label.get(field), extracted.get(field)) for field in FIELDS}


FieldTally = Counter[FieldOutcome]


def aggregate(document_scores: Sequence[Mapping[str, FieldOutcome]]) -> dict[str, FieldTally]:
    tallies: dict[str, FieldTally] = {field: Counter() for field in FIELDS}
    for doc_score in document_scores:
        for field in FIELDS:
            outcome = doc_score.get(field)
            if outcome is not None:
                tallies[field][outcome] += 1
    return tallies


def field_accuracy(tally: FieldTally) -> float | None:
    total = sum(tally.values())
    if total == 0:
        return None
    correct = tally[FieldOutcome.CORRECT] + tally[FieldOutcome.CORRECT_NULL]
    return correct / total


def generate_scorecard_markdown(tallies: Mapping[str, FieldTally], *, document_count: int) -> str:
    lines = ["# BriefPilot eval scorecard", ""]
    if document_count == 0:
        lines += [
            "**0 golden letters in `eval/golden/manifest.json`.** This scorecard proves the",
            "scoring mechanism runs end to end -- it is not an accuracy measurement. Real",
            "numbers appear here once real letters are collected (see `eval/golden/README.md`);",
            "fabricating them to fill this table would defeat the entire point of the eval",
            "suite.",
            "",
        ]
        return "\n".join(lines)

    lines.append(f"Scored against **{document_count}** golden letter(s).")
    lines.append("")
    lines.append("| Field | Accuracy | Correct | Correct (null) | Missed | Wrong | Hallucinated |")
    lines.append("|---|---|---|---|---|---|---|")
    for field in FIELDS:
        tally = tallies.get(field, Counter())
        accuracy = field_accuracy(tally)
        accuracy_str = "n/a" if accuracy is None else f"{accuracy:.0%}"
        lines.append(
            f"| {field} | {accuracy_str} | {tally[FieldOutcome.CORRECT]} "
            f"| {tally[FieldOutcome.CORRECT_NULL]} | {tally[FieldOutcome.MISSED]} "
            f"| {tally[FieldOutcome.WRONG]} | {tally[FieldOutcome.HALLUCINATED]} |"
        )
    lines.append("")
    lines.append(
        "**Hallucinated** is the failure mode this project's null-not-guess principle exists"
        " to prevent -- a non-zero count there is the single most important number in this"
        " table, more important than the headline accuracy percentage."
    )
    return "\n".join(lines)
