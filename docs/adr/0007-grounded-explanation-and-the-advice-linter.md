# ADR-0007 — Grounded explanation: two independent safeguards, not one

- **Status:** Accepted
- **Milestone:** M15
- **Date:** 2026-08-13

## Context

`CLAUDE.md` §1.2 and §5.4 describe the single highest legal-risk feature in
this product: a plain-English explanation of a German official letter that
**never gives legal advice**. Practicing law without a license
(Rechtsdienstleistungsgesetz, RDG) is a real offense in Germany, not a style
preference — an LLM that slips from "explaining what the letter says" into
"telling the user what they should do" turns a portfolio project into a
product with genuine legal exposure.

M15 also needed to retire `AIService.summarize` — an M1-era placeholder
(`SummarizationRequest{content, max_length}` / `SummarizationResult{summary}`)
with zero real callers and zero tests, written speculatively before any
milestone needed it. It doesn't fit M15's actual requirement: an explanation
grounded in both the raw letter text *and* the already-extracted structured
fields, not a generic "summarize this string" operation.

## Decision

**Replace `summarize` with `explain_document`**, taking
`DocumentExplanationRequest{content, extraction}` — the same "delete the
placeholder, name the real thing" move ADR-0004 made for
`DocumentExtractionResult`.

**Two independent safeguards enforce the no-advice rule, not one:**
1. `prompts/explain.py`'s system instruction explicitly forbids advice
   language and outside knowledge, grounding the model in only the letter
   text and extracted fields it's given.
2. `services/advice_linter.py`, a deterministic, curated regex check run on
   the model's *actual output* — never trusting the prompt alone to have
   worked. Same "don't just ask nicely, verify" discipline as every
   deterministic validator since M11 (D28, D31): a validator flags failures,
   it does not just hope the input was well-formed.

**A violation is flagged, never hidden or rewritten.** If the linter finds
advice-like phrasing, or the explanation exceeds 200 words or scores below
the Flesch Reading Ease readability target, the text is still shown, with a
visible warning attached. Silently rewriting or truncating LLM prose risks
producing something worse — an edited quote that reads as authoritative but
was never actually reviewed.

## Alternatives considered

**A single safeguard: prompt instructions only, no linter.** Rejected: every
other quality claim in this codebase (null-not-guess, OCR quality, extraction
validity, source-span linking) is backed by a deterministic check that
doesn't just trust the model — a legal-risk feature is the last place to make
an exception. Confirmed live: `gemini-3.5-flash` does not reliably honor
`response_mime_type="application/json"` (LEARNING.md's M14 post-merge fix,
bug 3) — direct evidence that trusting a model's instructions to hold
perfectly, unchecked, is not a safe assumption in this codebase generally,
let alone for RDG risk specifically.

**Retry/regenerate the explanation when the linter or readability check
fails.** Rejected for v1: retrying against a real API costs real free-tier
quota (a genuinely scarce resource — this session exhausted the 20-request/
day quota during testing) for a problem a flag already communicates
honestly. Worth revisiting once real usage data (M21+) shows how often
violations actually occur.

**Silently truncate to the 200-word limit, or auto-simplify low-readability
text.** Rejected: truncating prose can cut it off mid-sentence, and
"simplifying" text algorithmically without another LLM call (which reintroduces
the same grounding risk being guarded against) isn't achievable
deterministically. An honest flag beats a silently-mangled result.

## Consequences

- **`ExplanationResult` (JobResult-level) is separate from
  `DocumentExplanationResult` (raw AI-adapter output)** — the same split
  M9/M10/M11 established for extraction: `text` is what the model claims,
  `word_count`/`flesch_reading_ease`/`exceeds_word_limit`/
  `below_readability_target`/`advice_phrases_found` are what JobService can
  verify about that claim, computed after the AI call returns, not inside it.
- **Explanation is independent of extraction succeeding.** If extraction
  failed or is unconfigured, explanation still runs, grounded on an all-null
  `LetterExtraction` plus the raw OCR text — a letter with no confidently
  extracted fields still deserves an attempted explanation.
- **The `Disclaimer` component renders on every results view with content to
  disclaim about**, independent of whether this specific job produced an
  explanation — the disclaimer covers the extracted fields and OCR text too,
  not just the explanation text.
- **The advice-phrase linter is curated, not exhaustive** (`_ADVICE_PATTERNS`
  in `advice_linter.py`) — a phrase-pattern check can only catch surface
  patterns, not every way a model could phrase advice. It is a floor, not a
  guarantee, and not a substitute for a human legal review before this
  product would ever handle real user-facing legal risk at scale.

## Revisit when

- Real usage (M21+) shows how often the linter actually fires on real
  letters, and whether the curated pattern list needs expansion or produces
  false positives on legitimate restatement of a letter's own demands.
- A genuine, evidence-based case emerges for retry-on-violation instead of
  flag-on-violation, once free-tier quota economics or real user feedback
  justify spending an extra API call per flagged explanation.
