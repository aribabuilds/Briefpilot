# ADR-0003 — Free-tier LLM default (Gemini) and the `AIService` naming

- **Status:** Accepted
- **Milestone:** M8
- **Date:** 2026-07-31

## Context

The AI provider abstraction was built at M1, ahead of any milestone that actually
needed it, as groundwork for the dependency-inversion pattern. It shipped with
two adapters — `OpenAIService` and `AzureOpenAIService` — both metered, paid
APIs, with `AI_PROVIDER=openai` as the default. That directly conflicts with
`CLAUDE.md` §3's zero-cost mandate, which names Gemini Flash's free tier as the
intended default LLM. It was a known, tracked gap (`PROGRESS.md`'s Known
Deviations table) explicitly deferred to M8, where classification is the first
feature to actually call an LLM.

Separately, `CLAUDE.md` §4 names the wrapper `llm_client`; the actual
implementation is `AIService`. That naming drift was flagged at the same time,
for the same reason: resolve it once there's enough real usage (three
providers, three operations) to judge which name fits.

## Decision

**Add `GeminiService` and make `gemini` the default `AI_PROVIDER`.** OpenAI and
Azure OpenAI remain available as an explicit opt-in for anyone who has a paid
key and wants it, but nothing in the app calls a paid API unless a developer
deliberately sets `AI_PROVIDER=openai` or `azure_openai`.

**Keep the name `AIService`.** By M8 it exposes three operations —
`extract_document`, `summarize`, `classify_document` — across three providers.
`llm_client` describes a thin wrapper around one raw call; `AIService` more
accurately names a provider-agnostic capability interface, which is what the
abstraction actually is and what CLAUDE.md's own design intent describes
("Design the AI layer so AI providers are replaceable... future providers can
be integrated without changing business logic" — a *service* contract, not a
raw client).

## Alternatives considered

**Rename `AIService` to `llm_client`, matching the spec literally.** Rejected:
it would understate what the interface does (three structured operations, not
one generic completion call) and cost a mechanical rename across 3 adapters,
the factory, and every call site, for a naming preference rather than a
functional problem. If `CLAUDE.md` is later updated to match, that's a one-line
doc change; the code is already right.

**Default to OpenAI, require an explicit opt-in for Gemini.** Rejected: this is
exactly backwards from §3's intent — the *safe* default must be free, so that
cloning the repo and running `make dev` without any provider decision made
never risks a bill.

**Use a different free-tier provider (Hugging Face Inference API, a
self-hosted Ollama model).** Not evaluated in depth for M8: `CLAUDE.md`
explicitly names Gemini Flash, and it has a genuinely free tier (API key from
Google AI Studio, no billing account required) with better classification
accuracy on structured-output tasks than most locally-hosted small models
would give on CPU-only hardware. Ollama remains a good BACKLOG candidate if
Gemini's free-tier limits ever bite (see BACKLOG.md).

## Consequences

- **A missing `GEMINI_API_KEY` no longer breaks anything except classification
  itself.** `get_ai_service()` is only invoked when a job actually classifies
  (lazily, inside `JobService`'s best-effort classification block), so the app
  boots, uploads, OCRs, and passes the quality gate identically with or
  without a key. Classification degrades to `doc_type: null` — null-not-guess,
  not a crash — exactly the same discipline as the M5/M6 failure paths.
- **Getting a key is the owner's task**, not something Claude can do (creating
  accounts is out of scope regardless of permission). Documented in
  `backend/.env.example`.
- **The `AIService` interface now has three abstract methods** that every
  future adapter (Anthropic, a self-hosted model) must implement — a slightly
  higher bar per new provider, in exchange for one place that defines what
  "an AI provider" means to this app.

## Revisit when

- Gemini's free-tier rate limits or quotas prove insufficient once real usage
  exists (M13's accuracy-iteration decision point is the natural checkpoint).
- `CLAUDE.md` itself is updated to adopt `AIService` as the canonical name,
  which would let this ADR be marked as formally closing the spec gap rather
  than merely documenting a deliberate deviation from it.
