# ADR-0006 — Eval scoring taxonomy: five outcomes, not a pass/fail boolean

- **Status:** Accepted
- **Milestone:** M12
- **Date:** 2026-08-13

## Context

`CLAUDE.md` §5.5 calls the eval suite "a feature": golden letters as
fixtures, a per-field scorecard, a fast subset gated in CI. `PROGRESS.md`'s
M12 row asks for a scoring script, scorecard markdown, and a baseline run.
`eval/golden/` (M6) already froze the fixture format
(`manifest.json` + per-document `label.json`); M12's job is the harness that
reads those fixtures and decides what "correct" means.

The obvious version of that harness is a single accuracy percentage per
field: extracted value matches label, or it doesn't. That throws away exactly
the distinction this project's null-not-guess principle (`CLAUDE.md` §5.1)
exists to protect: a pipeline that says `null` when it doesn't know is
behaving correctly even though it "got the field wrong," and a pipeline that
invents a plausible-looking value the letter never had is a categorically
worse failure than either — the harness needs to be able to tell those apart,
or it can't actually measure whether null-not-guess is holding up on real
data.

## Decision

**Five outcomes per field, not a boolean:** `CORRECT`, `CORRECT_NULL` (both
label and extraction agree nothing was there), `MISSED` (label has a value,
extraction said null), `WRONG` (both non-null, but disagree), and
`HALLUCINATED` (label is null, extraction invented a value). `field_accuracy`
still reports one number for the scorecard's headline column (`CORRECT` +
`CORRECT_NULL` over the total), but the full breakdown — and specifically the
`HALLUCINATED` count — is always shown alongside it, called out in the
generated markdown as "more important than the headline accuracy percentage."

Implemented as a standalone `eval/scoring.py` with zero dependency on
`backend/app` — it operates on plain JSON-compatible dicts, the shape both
`label.json` and a `LetterExtraction` reduce to, so the comparison logic is
unit-testable with synthetic dicts and never needs Tesseract, an LLM call, or
even `backend/` to be importable.

## Alternatives considered

**One boolean per field (`correct: bool`).** Rejected: it can't distinguish
`MISSED` from `HALLUCINATED`, which is the one distinction that actually
matters for this product's core trust claim. A 90% accuracy score built
entirely out of hallucinated values that happened to be checked as "not
matching, so wrong" would look identical, in a single boolean-derived number,
to a 90% built out of honest nulls on the hard cases — two completely
different engineering situations a portfolio reviewer or a future prompt-
tuning pass needs to tell apart.

**A single `accuracy: float` per field with no per-outcome breakdown.**
Rejected for the same reason, one level up: a headline number is still useful
(it's kept), but publishing only the number and discarding the breakdown that
produced it would make the scorecard less honest than the fixture format
(`eval/golden/README.md`) it's built on top of.

**Fuzzy/similarity-based text matching (e.g., Levenshtein distance) instead
of normalized exact match.** Rejected for now: with 0 real letters, there is
no evidence yet for what a reasonable similarity threshold would even be, and
a wrong threshold would silently make `WRONG` extractions look like `CORRECT`
ones — the exact failure mode this ADR exists to prevent, just moved into the
comparator instead of the outcome taxonomy. Exact match after normalization
(case/whitespace folding for text, set-equality for lists, 2-decimal rounding
for amounts) is the honest default until real data justifies loosening it.

## Consequences

- **`run_eval.py` is dependency-injected the same way `JobService` already
  is** (`ClassifierRunner`/`ExtractorRunner` callables, reused directly from
  `app.services.job_service`), which is what let `eval/tests/test_run_eval_e2e.py`
  prove the real OCR + scoring wiring works against a real rendered document
  without a live LLM call — the same pattern `test_extraction_e2e.py`
  established for `JobService` at M10.
- **The scorecard is honest at 0 documents.** `generate_scorecard_markdown`
  writes an explicit "0 golden letters, not an accuracy measurement" message
  rather than an empty table or a fabricated one — the same posture M6's D15
  took for the fixture format itself.
- **CI now runs the harness on every push**, reusing the `backend` job's
  already-installed Tesseract and dev tools rather than a second job. Today
  this only proves the harness's own plumbing (0 documents, fast); it becomes
  the actual accuracy gate the moment `eval/golden/manifest.json` gains a
  first real entry, with no CI changes required.

## Revisit when

- Real golden letters land and the headline `field_accuracy` numbers need a
  place to be published beyond `eval/scorecard.md` (M25's full 30-letter run
  and failure analysis is the natural point to also improve presentation).
- A genuine, evidence-based case for fuzzy text matching emerges from real
  `WRONG` outcomes that are actually near-misses (OCR noise in a sender name,
  say) — argued from real failure data, not guessed in advance.
