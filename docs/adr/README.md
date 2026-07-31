# Architecture Decision Records

An ADR captures a decision that is **expensive to reverse** — one where a future
reader would otherwise ask "why on earth is it like this?" and get no answer.

Routine choices (a library version, a file name) do not get an ADR. Things that
constrain later milestones do.

## Index

| # | Title | Status | Milestone |
|---|-------|--------|-----------|
| [0001](0001-local-first-zero-cost-demo-strategy.md) | Local-first, zero-cost demo strategy (no hosted deployment) | Accepted | M1 |
| [0002](0002-ocr-and-coordinate-schema.md) | OCR engine (Tesseract) and the normalized coordinate schema | Accepted | M3 |
| [0003](0003-free-tier-llm-default-and-aiservice-naming.md) | Free-tier LLM default (Gemini) and the `AIService` naming | Accepted | M8 |
| [0004](0004-extraction-schema-one-schema-not-per-type.md) | Extraction contract: one common `LetterExtraction` schema, not per-type | Accepted | M9 |

## Planned

The execution plan names four decisions that must not silently change later; each
gets an ADR when it is actually made, not before:

- **No-account / session model** (M22) — retrofitting privacy architecture is a rewrite.
- **Eval harness format** (M12) — golden fixtures are an investment; churning their
  schema burns it.

## Format

Each record uses the same headings: **Context**, **Decision**, **Alternatives
considered**, **Consequences**, **Revisit when**. Write it in plain language, on the
day the decision is made — a reconstructed ADR reads like a reconstructed ADR.

Status is one of `Proposed`, `Accepted`, `Superseded by ADR-NNNN`. Records are
immutable once accepted: to change a decision, write a new ADR that supersedes it.
