# ADR-0010 — Hardening stays in-process; LLM prompts get defense-in-depth, not a gateway

- **Status:** Accepted
- **Milestone:** M24
- **Date:** 2026-08-14

## Context

M24's story is "the service stays responsive and safe even under load or abusive input." The
execution plan names five concrete items: rate limiting, size guards, structured logging, an uptime
monitor, and guardrails. Three of these (rate limiting, streaming size guards, request logging) are
classic API-hardening concerns; "guardrails" in a project whose pipeline calls a third-party LLM on
user-uploaded content also has to mean something more specific — resistance to prompt injection, not
just input validation. The zero-cost mandate (CLAUDE.md §3) and ADR-0001's "no hosted deployment"
stance both bear directly on how far each of these can reasonably go.

## Decision

**Rate limiting and size guards stay in-process, matching ADR-0009's retention sweep.** A new
`services/rate_limiter.py::RateLimiter` is an in-memory, per-IP sliding-window limiter (no Redis, no
API gateway), wired via a FastAPI dependency (`enforce_rate_limit`) onto the two state-changing
endpoints (`POST /jobs`, `DELETE /jobs/{id}`). The existing upload size check (`max_upload_bytes`,
M2) is hardened from "read the whole body, then check its length" to bounded chunked reads
(`api/jobs.py::_read_bounded`) that reject the moment the running total exceeds the limit, so an
oversized upload is never fully received before being turned away.

**Request logging extends the existing structlog pipeline**, not a new system: a single
`main.py::log_requests` middleware emits one `http_request` event per request (method, path, status,
duration, client IP) through the same `configure_logging()` setup M1 already established. No new
dependency.

**LLM prompt hardening is defense-in-depth, not a rewrite of the pipeline's trust model.** A shared
`services/ai/prompts/__init__.py::wrap_untrusted_content()` delimits the letter's OCR'd text in all
three prompts (classify/extract/explain), paired with an explicit system-prompt instruction
(`UNTRUSTED_CONTENT_INSTRUCTION`) never to treat delimited content as instructions. This sits
alongside, not instead of, the deterministic output-side checks that already exist:
`validators.py` (M11) and `advice_linter.py` (M15) don't trust the prompt to have worked — they
verify what the model actually returned.

**No uptime monitor was built.** CLAUDE.md §3 names Uptime Kuma as an acceptable free option, but an
uptime monitor's entire job is watching something that's reachable from outside the process it runs
in — and per ADR-0001, this project deliberately has no hosted deployment to watch. The existing
`GET /health` endpoint (M1) already is the extensibility point a real monitor would poll; standing
one up now, with nothing to point it at, would be infrastructure theater; the honest answer, matching
M1's own "skeleton deployed ❌ by design" framing, is that this item doesn't apply yet.

## Alternatives considered

**A dedicated rate-limiting library** (`slowapi`, `fastapi-limiter`). Rejected: both assume or
strongly prefer a Redis backend for anything beyond a single process, which this app doesn't have and
doesn't need at demo scale — the same reasoning ADR-0009 already applied to retention. `RateLimiter`
is ~30 lines and fully covers the actual requirement (per-IP, in-process, testable with an injected
clock).

**An LLM-based or third-party prompt-injection detector** (e.g., a separate classifier call
screening input before the real prompt runs). Rejected on both cost and effectiveness grounds: it's
a second paid-tier-adjacent API call per upload (violates CLAUDE.md §3 spirit even on a free tier, by
doubling LLM traffic for uncertain benefit), and a classifier can itself be evaded by the same class
of attack it's meant to catch. The instruction-plus-delimiter approach is free, and — critically —
isn't asked to be the actual security boundary; `validators.py`/`advice_linter.py` are, because they
check output, not intent.

**Standing up Uptime Kuma against `GET /health` anyway**, monitoring the local dev server, purely to
have satisfied the plan's literal wording. Rejected: a monitor watching `localhost` provides no real
signal (it would never fire, since the developer's own machine being off means there's no monitor
running either) and would misrepresent the project's actual operational maturity to a reader of
`PROGRESS.md` — the same "don't claim something the code doesn't do" principle CLAUDE.md §5.6 applies
to privacy claims applies here to operational claims too.

## Consequences

- **Rate limiting and the retention sweep share the same known limitation**: per-process state,
  reset on restart, no cross-instance coordination. Acceptable now (single zero-cost process, ADR-0001);
  revisit together if this app is ever deployed as more than one instance.
- **The prompt-injection defense is honestly bounded.** `wrap_untrusted_content()` and
  `UNTRUSTED_CONTENT_INSTRUCTION` reduce the odds a model treats embedded text as instructions; they
  cannot guarantee it. `test_prompts.py` proves the wiring (every prompt delimits its content, every
  system instruction states the rule) — it cannot and does not claim to prove the model always obeys
  it. The real backstop remains output-side validation, unchanged by this ADR.
- **The uptime-monitor gap is now on the record**, not silently absent: `PROGRESS.md`'s M24 row and
  this ADR both name it as deferred to whenever a real hosted target exists (M29's launch checklist,
  if a free hosting tier is ever proposed and approved), not forgotten.

## Revisit when

- This app is ever deployed as more than a single local process: the rate limiter and retention
  sweep both need a shared backing store instead of in-memory per-process state.
- A free hosting tier is proposed and approved (CLAUDE.md §3's escalation protocol) at M29: an uptime
  monitor against the real deployed URL becomes meaningful, and should be built then, not before.
