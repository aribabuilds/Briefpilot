"""Structured extraction contract — FROZEN as of ADR-0004.

Per CLAUDE.md §4, this is the contract between the pipeline and the frontend
and must not change once golden fixtures (eval/golden/) exist. One common
schema across all 8 in-scope letter types, not per-type schemas — see
ADR-0004 for why: CLAUDE.md §1 already defines a single field list (sender,
dates, deadlines, amounts, required actions, legal references) shared across
every type, and there are zero real letters yet to justify diverging from it.

Every field is wrapped in ExtractedField: null-not-guess (CLAUDE.md §5.1) is
enforced by making "not found" a real, representable state (value=None) rather
than something the caller has to infer from an empty string or a sentinel.

`amount` is a Decimal, not a float — money should never accumulate binary
floating-point error. Pydantic serializes Decimal to a JSON *string*
("184.50"), not a number, specifically to preserve that precision; the
frontend must treat it as a string, not parse it as a JS number.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.ocr import BBox


class SourceSpan(BaseModel):
    page: int  # 0-based, matches OcrPage.page
    # One box per matched OCR word (not a single merged box): the overlay
    # (M18) can choose to draw one rectangle per word or a merged region: the
    # per-word geometry survives either choice, but a pre-merged box couldn't
    # be split back apart.
    bboxes: list[BBox]


class ExtractedField[T](BaseModel):
    # None means "not found in the letter" — never a guessed or fabricated
    # value. Enforced in the extraction prompt AND here: a parser that can't
    # confidently produce a value must set this to None, not its best guess.
    value: T | None
    confidence: float  # [0, 1]
    # None exactly when value is None — nothing to point back to.
    source_span: SourceSpan | None = None


class LetterExtraction(BaseModel):
    sender: ExtractedField[str]
    letter_date: ExtractedField[date]
    deadline: ExtractedField[date]
    amount: ExtractedField[Decimal]
    legal_references: ExtractedField[list[str]]
    required_actions: ExtractedField[list[str]]
