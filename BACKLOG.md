# BACKLOG — BriefPilot

**Scope is FROZEN** (`CLAUDE.md` §2). Nothing here enters a milestone without an explicit
swap: if something comes in, something comes out. Ideas land here — mine or the owner's —
never in the current milestone.

**Categories:** `Out of MVP` (decided, documented) · `Nice to Have` · `Production Feature` ·
`Future Enhancement`

---

## Out of MVP (decided — do not relitigate)

These were cut deliberately in the execution plan and `CLAUDE.md` §2. Each is a good 90-day
feature; none is needed to demonstrate the core engineering value.

| Item | Why it's out |
|------|--------------|
| Reply drafting (generating responses to authorities) | ~1 week of work; raises RDG/legal-advice risk sharply; doesn't strengthen the extraction-pipeline story |
| Multi-letter case management / case threads | ~1 week; needs accounts, which the privacy model deliberately avoids |
| User accounts / auth | Privacy claim is "no accounts"; retrofitting later is a rewrite, so the *absence* is architectural, not laziness |
| Additional output languages beyond English | Each language multiplies eval-suite cost; depth beats breadth |
| Native mobile apps | Responsive PWA covers the demo; native is pure cost |
| Billing / subscriptions / payments | Portfolio project, not a commercial product |

## Nice to Have (would improve the demo; cut first under pressure)

Contingency cut order from the plan: **glossary popovers → 8th/7th doc types → analytics polish.**
Never cut: validators, eval suite, deletion, disclaimer.

| Item | Notes |
|------|-------|
| Glossary popovers (M16) | First thing cut if M15–M21 slips |
| Doc types 7 and 8 | Narrow to 5 types if extraction accuracy plateaus (M13 decision point) |
| Analytics polish | Basic structured logging is enough for the MVP |
| Dark-mode screenshot set | Only if M21 has slack |

## Production Feature (real product would need; MVP does not)

| Item | Notes |
|------|-------|
| Paid OCR provider (Azure Document Intelligence / Google Vision / Mistral) | Adapter is designed for a config swap; blocked by §3 zero-cost mandate. Requires owner approval + cost estimate |
| Paid LLM provider (OpenAI / Azure OpenAI) | Adapters already exist in `backend/app/services/ai/providers/` but must not be the default. See PROGRESS.md "Known deviations" |
| Hosted deployment (EU region) | Plan assumed Hetzner/Fly/Vercel; §3 forbids provisioning. May be *proposed* if a genuinely free, no-card tier fits |
| Sentry error tracking | Free tier allowed **only** if no card is required — verify before proposing |
| Horizontal scaling / job queue (Celery, RQ) | Current design is synchronous + polling; fine for demo load |
| Multi-tenancy | Requires accounts (out of scope) |
| Real Postgres persistence (CLAUDE.md §4 names this as decided) | `JobRepository`/`DocumentStore` have been in-memory only since M2/M18 — no driver in `requirements.txt`, `Settings.database_url` is unread. Deliberate for a single free process (ADR-0001) and it's what makes 24h auto-purge/one-click delete simple to verify (ADR-0009); `docker-compose.yml`'s Postgres container is unconnected scaffold. Needed once this runs as more than one instance or has to survive a restart — see docs/ARCHITECTURE.md's "Known deviation: Postgres" |

## Future Enhancement (post-MVP, Sprint 5+ candidates)

| Item | Notes |
|------|-------|
| Local/self-hosted LLM via Ollama | Strongest long-term fit for the $0 mandate — no rate limits, no key, fully offline. Rejected for MVP because free-tier hosted (Gemini Flash) gives better extraction quality per unit of effort, and quality drives the eval scorecard the portfolio is built on. Revisit if free-tier limits bite |
| Confidence calibration study | Turn confidence tiers from heuristic into measured; strong interview material |
| Human-in-the-loop correction UI | Users fix a field, corrections feed the golden set |
| Active learning from corrections | Depends on the above |
| Letter-type auto-router to specialist prompts | Only worth it beyond ~8 doc types |
| Deadline calendar export (.ics) | Small, high user value, zero architectural risk |

---

## How to add an item

1. Add a row to the right category with a one-line "why".
2. If it's a scope *addition* to the current MVP, name what it replaces — and get the owner's
   explicit confirmation before anything moves.
