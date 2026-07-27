# ADR-0001 — Local-first, zero-cost demo strategy (no hosted deployment)

- **Status:** Accepted
- **Milestone:** M1
- **Date:** 2026-07-27

## Context

The 30-day execution plan specifies, as an M1 task, an "EU-region deploy target
(e.g. Hetzner/Fly EU or Vercel fra1 + EU backend), Sentry EU," with the acceptance
criterion "CI-green deploys on push." Sprint 1's demo is described as happening "on
the live URL."

That plan assumes a funded project. This one is not: `CLAUDE.md` §3 sets a hard
zero-cost mandate, and the two documents genuinely conflict on this point.

There is a second, less obvious pressure. BriefPilot processes photographs of German
official letters — Finanzamt notices, residence-permit correspondence, medical
insurance. Even with no accounts and a 24-hour purge, hosting that data anywhere
means making a real GDPR claim about a real processor in a real jurisdiction.

## Decision

**No hosting is provisioned.** The project runs locally via `make dev` (Docker
Compose: frontend + backend + Postgres). The demo deliverable is a recorded video
plus a README a recruiter can follow on a clean machine to reproduce the whole
system.

`CLAUDE.md` §3 wins over the execution plan wherever the two conflict. A free tier
may later be **proposed** — never silently provisioned — and only if it requires no
card and has no silent truncation limits.

Sentry is likewise deferred. Its free tier is permitted by §3 only if no card is
required; that has not been verified, so it is not adopted. Structured logging
(already in `app/core/logging.py`) covers M1's needs.

## Alternatives considered

**1. Provision a free hosting tier now (Fly.io, Render, Vercel hobby).**
Rejected for M1. Free tiers that ask for a card are one forgotten cron away from a
bill, and a cold-starting free dyno makes a *worse* recruiter demo than a local run
that always works. Deferred, not refused — worth revisiting once the pipeline exists.

**2. Follow the plan and deploy to Hetzner/Fly EU.**
Rejected: costs money, which the mandate forbids outright.

**3. Deploy the frontend only (static/Vercel), backend local.**
Rejected as the worst of both: a public URL that looks live but cannot process a
letter is actively misleading to exactly the audience it is meant to impress.

## Consequences

**Accepted costs.**
- No public URL. The Sprint-1 demo becomes a screen recording, not a live link.
- "Works on my machine" risk is real and shifts weight onto M28's clean-machine test.
- No production error tracking; failures surface through logs, not alerts.

**Benefits.**
- Zero spend, permanently — the project can sit in a portfolio for years without a bill.
- No third-party processing of sensitive documents, so the privacy page can make a
  claim the code actually honours (§5.6) rather than a hedged one.
- Reproducibility becomes the deliverable, which is itself an engineering signal: a
  recruiter who can `make dev` your project learns more than one who clicks a URL.

**Interview framing.** "Why no live demo?" has a strong answer — a deliberate cost
and data-protection trade-off, with the mitigation (reproducible local stack,
verified on a clean machine) built into the plan. That is a better story than an
unexplained free-tier deployment.

## Revisit when

- A genuinely free, no-card, EU-region tier is identified **and** the pipeline is
  complete enough to demo end-to-end (earliest M22, realistically M26+); or
- the owner decides a live URL is worth a specific monthly cost, which is her call
  and requires the §3 escalation protocol: what was tried free, cheapest paid
  option, exact cost, and what staying free would sacrifice.
