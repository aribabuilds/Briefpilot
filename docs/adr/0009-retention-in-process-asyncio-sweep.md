# ADR-0009 — Retention enforced by an in-process asyncio sweep, not an external scheduler

- **Status:** Accepted
- **Milestone:** M22
- **Date:** 2026-08-14

## Context

ADR-0008 named the gap explicitly: since M18, uploaded document bytes and job records persist in
`InMemoryJobRepository`/`InMemoryDocumentStore` for the process's entire lifetime, with no expiry.
CLAUDE.md §5.6 requires "one-click delete verified at storage layer, 24h auto-purge" and that "the
privacy page never claims something the code doesn't do." There are two distinct mechanisms needed:
a user-triggered delete (fast, one request) and a time-triggered purge that runs even if the user
never asks (the actual privacy guarantee — most users won't click delete).

The zero-cost mandate (CLAUDE.md §3) rules out anything that needs its own infrastructure: no cron
daemon, no external task queue (Celery/RQ + a broker), no scheduled cloud function. Whatever runs the
sweep has to live inside the same FastAPI process that's already running for free.

## Decision

**Both mechanisms extend the existing repository interfaces** rather than introducing a new
abstraction: `JobRepository` and `DocumentStore` each gained `delete()` (M22's one-click path) and
`JobRepository` gained `list_all()` (needed only by the sweep, to find what's expired). A new pure
function, `services/retention.py::purge_expired(repository, document_store, *, now, max_age)`,
computes which job ids are expired and deletes them from both stores — same split as
`validators.py`: the *rule* ("older than max_age") is trivially unit-testable in isolation, agnostic
of any clock or event loop.

**The sweep itself runs as a background `asyncio.Task`, started in a FastAPI `lifespan` context
manager** (`main.py`), looping `await asyncio.sleep(retention_sweep_interval_seconds)` then calling
`JobService.purge_expired()`. No new dependency, no new process, no new deploy target — it lives and
dies with the app server that's already running per ADR-0001's local-first strategy.

## Alternatives considered

**A cron job / OS-level scheduled task** invoking a CLI script. Rejected: assumes a persistent host
with a crontab, which conflicts with the "runs via `make dev` / Docker Compose, no provisioned
infrastructure" demo strategy (ADR-0001). It would also need its own DB/storage connection story
duplicate to the app's, for no benefit at this scale.

**Lazy expiry-on-read** (check `created_at` inside `get()`/`get_document()` and treat expired
entries as absent, without ever actually deleting them). Rejected: this satisfies "the user can't
retrieve expired data" but not "the data is actually gone" — CLAUDE.md's own bar is that privacy
claims must match what the code *does*, and unreachable-but-still-resident bytes in an in-memory dict
is not the same claim as deleted. It would also leak memory indefinitely on a long-running process,
which a zero-cost single-instance deployment can't absorb forever.

**A dedicated task-scheduling library** (e.g. APScheduler). Rejected as unnecessary weight for one
job on one interval — CLAUDE.md §4's "NO LangChain-style heavy frameworks, ~200 lines of own
orchestration" spirit applies here too; `asyncio.sleep` in a loop is the whole feature.

## Consequences

- **The retention window and the sweep's promptness are two independent settings**
  (`retention_max_age_hours`, `retention_sweep_interval_seconds`) — an hourly sweep interval means an
  expired job can live up to ~1 hour past its nominal 24h cutoff before being swept. This is a
  documented approximation, not silently rounded away: the privacy page (M23) must say "auto-purged
  within 24h" in a way that's honestly compatible with an hourly sweep, not "at exactly 24h."
- **The sweep task is invisible to any test that doesn't explicitly start `main.py`'s lifespan** —
  by design. Its own logic (`purge_expired`) is fully unit-tested without a real clock or event loop;
  the scheduling wrapper around it is intentionally as thin as `JobService.get_job_service()`'s own
  wiring, which this project has consistently chosen not to over-test (see M1–M20's pattern of
  testing pure logic heavily and thin wiring lightly).
- **Restarting the process resets the sweep's timer, not the data's age** — `created_at` lives on the
  `Job` record itself, so a restart mid-window doesn't extend any job's life; it only pauses sweeping
  until the loop's first `asyncio.sleep` completes again after startup, which is a bounded,
  self-correcting gap (at most one `retention_sweep_interval_seconds`), not a permanent leak.
- **`JobRepository.list_all()` doesn't scale past an in-memory demo** — a real datastore should
  replace it with an indexed `WHERE created_at < ...` query rather than materializing every job on
  every sweep. Acceptable now (`InMemoryJobRepository` is the only implementation, per ADR-0001); a
  Postgres-backed repository would implement the same interface differently, no caller changes.

## Revisit when

- A real (non-in-memory) `JobRepository`/`DocumentStore` implementation lands: `list_all()` should
  become a bounded, indexed query, not a full materialization.
- M23's privacy page copy is written: it must describe the sweep's actual cadence (hourly, not
  instantaneous-at-24h) rather than a rounder claim the code doesn't quite make true.
