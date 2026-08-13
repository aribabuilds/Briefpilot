# ADR-0005 — `validation_issues`: an additive field on the frozen `ExtractedField`

- **Status:** Accepted
- **Milestone:** M11
- **Date:** 2026-08-13

## Context

`CLAUDE.md` §5.2 requires deterministic validators — "dates parse; deadlines ≥
letter date; legal references checked against a curated § whitelist; amounts
numeric" — and is explicit that "validator failures downgrade confidence and
flag, never silently fix." ADR-0004 froze `ExtractedField[T]` at
`{value, confidence, source_span}` — no fourth field existed to carry a flag.

"Dates parse" and "amounts numeric" are already guaranteed one layer up: the
extraction parser (M9) degrades anything that fails to coerce to `date` /
`Decimal` to `None` before a `LetterExtraction` is ever constructed. What M11
actually needed to add was semantic, cross-field validation no type system
enforces on its own — a `deadline` earlier than its own `letter_date`, a
negative `amount`, a `legal_references` entry that doesn't match any real
German statute abbreviation — and a place to record that a check failed.

## Decision

**Add `validation_issues: list[str] = []` to `ExtractedField[T]`.** A new
`services/validators.py` (mirroring `source_span_linking.py`'s shape: pure
functions, zero network, exhaustively unit-tested) runs after source-span
linking and, on a failed check, appends a machine-readable code (e.g.
`"deadline_before_letter_date"`) and caps confidence at
`VALIDATION_FAILURE_CONFIDENCE_CAP = 0.2` — lower than source-span linking's
`UNVERIFIED_CONFIDENCE_CAP = 0.4`, because a self-contradictory value is a
stronger signal of being wrong than a merely-unlinked one. The value itself is
never rewritten.

This is additive, not a breaking change to the frozen contract: every existing
caller that constructs an `ExtractedField` without the new field still works
(Pydantic default `[]`), and every consumer that doesn't know about it yet
(the M9/M10 test suites) is unaffected.

## Alternatives considered

**A separate `ValidationResult` object alongside `LetterExtraction`,
correlating issues to fields by name.** Rejected: it would decouple a field's
value from the reason it isn't fully trusted, forcing the frontend to
cross-reference two structures to render one badge. Keeping the flag on the
field it describes is the same locality-of-information argument ADR-0004 made
for embedding `BBox`es directly in `SourceSpan` rather than indices into a
separate `OcrDocument`.

**A single boolean (`is_valid: bool`) instead of a list of codes.** Rejected:
a field can fail more than one check at once in principle (not yet possible
given today's three rules, but true the moment a fourth rule exists), and a
boolean discards *why* — which the frontend already needs to render a useful
tooltip, and which an eval scorecard (M12) will need to break down failures by
category rather than one undifferentiated "invalid" bucket.

**Zero the value's confidence instead of capping it.** Rejected for the same
reason D26 rejected zeroing an unlinkable value: a `deadline` before its
`letter_date` is very likely a real extraction error, but "very likely" is not
"certainly" — the letter itself could be genuinely unusual (a retroactive
notice, a corrected date). Confidence 0 claims certainty this project's own
null-not-guess principle doesn't have grounds to claim.

## Consequences

- **The frontend contract grows by one field.** `types/job.ts`'s
  `ExtractedField<T>` gained `validation_issues: string[]`; `ExtractionSummary`
  renders a `⚠ flagged` badge, with the human-readable reason in a tooltip, next
  to the existing verified/unverified badge — the two are independent signals
  (a field can be OCR-verified *and* semantically flagged at the same time).
- **Confidence capping now composes across two independent mechanisms.**
  Source-span linking runs first (M10) and may already cap a value to `0.4`;
  validation runs second and may cap it further to `0.2`. Neither mechanism
  raises what the other lowered — `min()` at each step guarantees the final
  confidence is never higher than the stricter of the two.
- **The § whitelist is curated, not exhaustive** (`_KNOWN_LAW_CODES` in
  `validators.py`) — a real citation outside it is flagged as unrecognized,
  not rejected, consistent with null-not-guess: don't silently drop what might
  be real, but don't let it pass unquestioned either.

## Revisit when

- Real golden letters (M12/M13) reveal false positives in the § whitelist or
  the deadline/amount rules, at which point the specific rule — not the
  `validation_issues` mechanism itself — should change.
- `VALIDATION_FAILURE_CONFIDENCE_CAP` and `UNVERIFIED_CONFIDENCE_CAP` need
  real-data tuning together, since they now interact (M13's decision point,
  same posture as every other threshold in this codebase).
