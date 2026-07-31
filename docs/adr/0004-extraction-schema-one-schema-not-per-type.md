# ADR-0004 — Extraction contract: one common schema, not per-type

- **Status:** Accepted
- **Milestone:** M9
- **Date:** 2026-08-01

## Context

`CLAUDE.md` §4 names this the second of four "must not change once fixtures
exist" decisions: per-type Pydantic schemas with `{value, confidence,
source_span}` field wrappers, the contract between pipeline and frontend. The
execution plan's own Day 9 task list says "Pydantic schemas for top-4 types +
generic" — implying up to 5 distinct schemas (4 bespoke + 1 fallback).

`CLAUDE.md` §1, however, already defines a single field list that the product
extracts from *every* letter type, regardless of sender: sender, doc type,
dates, deadlines, amounts, required actions, legal references. There is also
no golden-letter data yet (`eval/golden/` is still empty) to reveal whether
the 8 in-scope types actually need structurally different fields, or whether
they only differ in which fields tend to be populated.

## Decision

**One common schema, `LetterExtraction`,** used for every letter type:
`sender`, `letter_date`, `deadline`, `amount`, `legal_references`,
`required_actions` — each wrapped in a generic `ExtractedField[T]` carrying
`{value, confidence, source_span}`. `doc_type` is not part of this schema; it
is already produced separately by classification (M8) and lives on
`JobResult`, not duplicated here.

`SourceSpan` (`{page, bboxes: list[BBox]}`) reuses the **frozen M3 `BBox`**
directly, so the overlay (M18) needs no coordinate math beyond what it already
has for OCR words.

`ExtractedField` uses PEP 695 native generic syntax (`class
ExtractedField[T](BaseModel)`), not the classic `TypeVar`/`Generic[T]`
pattern — verified working against the installed Pydantic (2.13), and the
`pydantic` floor was raised to `>=2.11` (where this support landed) to
guarantee it holds in any fresh environment, not just this one.

## Alternatives considered

**Four bespoke per-type schemas + one generic fallback, per the plan's literal
text.** Rejected for now: with zero real letters collected, any per-type field
differences would be guessed, not observed — exactly the kind of speculative
design this project's own principles (M6's refusal to fabricate golden
letters; M9's own "eval vs labeled set" deferral) argue against. A single
schema is also simply less to freeze wrong. If real data later shows, say,
`bussgeld` letters need a `violation_type` field that `krankenkasse` letters
never have, that becomes a deliberate, evidence-based ADR superseding this one
— not a guess made now.

**`source_span` as word indices into `OcrDocument.words`, not embedded
`BBox`es.** Rejected: it would make every `ExtractedField` dependent on also
holding a reference to the exact `OcrDocument` it was extracted from, and
re-deriving geometry via index lookups at render time. Copying the matched
words' `BBox`es directly makes `ExtractedField` self-contained — the overlay
can render a highlight from the field alone, with no other object in hand.

**Reuse `DocumentExtractionResult` (the M1 placeholder) by nesting
`LetterExtraction` inside it.** Rejected: `DocumentExtractionResult` was a
speculative `dict[str, Any]` written before this shape was known, with zero
real callers. Keeping it as a wrapper around the real schema would mean two
names for one concept, forever. `AIService.extract_document` now returns
`LetterExtraction` directly.

## Consequences

- **Source-span linking is explicitly out of scope for M9.** Every
  `ExtractedField.source_span` returned by `parse_letter_extraction` is
  `None` — the LLM only ever sees flattened OCR text, not word positions, so
  it cannot honestly claim a bounding box. Matching a value back to specific
  OCR words is M10's job, once the pipeline actually holds the `OcrDocument`
  to match against.
- **`amount` is `Decimal`, not `float`** — money should not accumulate binary
  floating-point error. Pydantic serializes `Decimal` to a JSON **string**
  (verified: `"184.50"`, not `184.50`) to preserve that precision — the
  frontend must treat it as a string, never `parseFloat` it blindly for
  further arithmetic.
- **The parser never raises.** Malformed JSON, a missing field, or a value
  that fails to coerce to its real type (a bad date string, non-numeric
  amount) degrades that one field to `null` at confidence `0.0` — the same
  null-not-guess discipline as OCR quality (M6) and classification (M8),
  applied per-field rather than to the whole response.
- **Not yet wired into `JobService` or `JobResult`.** M9 ships the schema,
  the prompt, and the parser, unit-tested with no network call. Running this
  live against a real letter, and computing real source spans, is M10.

## Revisit when

- Real golden letters (once collected) show a genuine, evidence-based need for
  per-type fields the common schema can't express — write a new ADR
  superseding this one rather than quietly special-casing a type.
- M10's source-span linking design may reveal that `bboxes: list[BBox]` needs
  adjustment (e.g., a value spanning two non-adjacent OCR regions) — expected
  to be additive, not a breaking change to the wrapper shape itself.
