# Launch checklist (M29)

"Live and monitored" for this project doesn't mean a public URL with an uptime monitor —
ADR-0001 deliberately has no hosted deployment, and ADR-0010 deliberately didn't build a monitor
with nothing real to point it at. What it does mean: the local demo runs reliably end to end, the
operational visibility that exists (health endpoint, structured logs) actually works, and the public
face of the project (the GitHub repo) honestly reflects what's built. Checked against real runs, not
assumed from having built the thing.

## Functionality — verified

- [x] Upload → OCR → classify → extract → validate → explain → done, live-verified repeatedly
  across M18–M28 (curl + Browser pane), including with a real Gemini key
- [x] Quality gate: a deliberately bad/empty document correctly routes to `low_quality`, no garbled
  text shown (M6, re-confirmed live during M22's delete test)
- [x] Click-to-highlight: verified field selection scrolls to and pulses the correct bbox (M19,
  Playwright)
- [x] One-click delete: live-verified end to end (page served → delete → 404 on job and page →
  second delete also 404) — M22
- [x] 24h auto-purge: unit-tested with an injected clock (`purge_expired`); the background sweep
  loop itself boots correctly (confirmed in server logs) — M22
- [x] Privacy page content matches the actual delete/retention/AI-provider behavior — M23
- [x] Rate limiting: live-verified — 20 requests handled normally, 21st/22nd got `429` — M24
- [x] Request logging: live-confirmed structured `http_request` log line in real server output — M24

## Tests — verified

- [x] 245 backend tests pass, including in a **genuinely fresh venv** built from
  `requirements-dev.txt` alone (M28) — not just the long-lived populated dev environment
- [x] `ruff`, `black --check`, `isort --check`, `mypy --strict` all clean, fresh venv included
- [x] 6 Playwright specs pass against the real rendered frontend (backend calls mocked)
- [ ] Frontend dependency install **not** re-verified in an isolated copy (M28) — relies on repeated
  clean builds from the same lockfile across M20/M22/M23/M26, not a fresh `npm ci`

## Privacy claims match implementation

- [x] No accounts anywhere in the codebase
- [x] Storage is in-memory only — confirmed no Postgres driver in `requirements.txt`, confirmed
  `Settings.database_url` is unread (M26) — so "gone on restart" is literally true, not aspirational
- [x] 24h ceiling: real, sweep-verified, hourly cadence honestly stated (not "instant at 24h")
- [x] Third-party disclosure: `/privacy` states the letter's OCR'd text (never the image) goes to
  Google's Gemini API — verified this is literally what `GeminiService`/prompt builders do (M24)
- [x] Logs never contain letter content — verified via a real `structlog.testing.capture_logs()` test
  that the response body isn't logged (M24)

## Documentation

- [x] `README.md` and `docs/ARCHITECTURE.md` rewritten to match the actual current system (M26),
  including a real gap they surfaced (Postgres never wired) rather than hiding it
- [x] 10 ADRs (`docs/adr/0001`–`0010`), each written the day the decision was made
- [x] `PROGRESS.md` reflects true status per milestone — `done`/`partial`/`blocked`, never a false
  `done`
- [x] `BACKLOG.md` carries every deliberately-deferred item, including the Postgres gap M26 found
- [x] `LEARNING.md` has a full Decisions/Review/Teach-back section for every milestone that shipped
  code; blocked milestones (M13, M21, M25) correctly have none

## Known, honestly-tracked gaps (not blockers to "done," but real)

- M13/M25: eval accuracy measurement blocked on real golden letters (0 collected) — cannot be
  fabricated without defeating the point of the eval suite
- M21: real phone-user testing blocked on real testers — script prepared, sessions not run
- M27: demo video is the owner's task — a real recording (`Sprint 4 - video/1.webm`) already exists,
  not yet edited/published
- M28: frontend fresh-install not independently re-verified (see Tests, above)
- Docker Compose / Postgres: present in the repo, explicitly marked unverified against the current
  in-memory-only implementation (M26)

## The actual launch blocker this checklist found

**The public GitHub repo is 14 commits behind local `main` — frozen at M14 (2026-08-13).**
Everything from M15 onward (grounded explanation, checklist/glossary, document viewer,
tap-to-highlight, the full regression suite, one-click delete, the privacy page, and all of M24's
hardening) exists only locally. A hiring manager visiting the repo right now would see roughly half
the project. GitHub Actions has not run against any of this work — "CI green" above is true of local
runs (ruff/black/isort/mypy/pytest, all re-verified in a fresh venv for M28) but has not been
confirmed against the actual CI environment, since nothing has triggered it since M14.

This also means 14 commits' worth of work — everything built under the "full speed, review later"
authorization from M11 onward — has not yet been reviewed by the owner. Pushing makes it public
before that review happens. **Not pushed. This is the owner's call, not something to do silently.**

## Monitoring — what actually exists (no hosted target, per ADR-0001/ADR-0010)

- `GET /health` and `GET /version` — both live-verified this session (M28's fresh-venv boot test)
- Structured `http_request` logs (M24) — the closest thing to observability this app has
- No uptime monitor, because there is nothing deployed for one to watch (ADR-0010) — revisit only if
  a free hosting tier is ever proposed and approved

## Bottom line

Everything **within this session's control** is genuinely verified, not just claimed: tests pass in
isolation, privacy claims match code, hardening works live, docs match reality. The one real launch
blocker is entirely about publication, not engineering: **the commits need to be reviewed and pushed**
before this project can honestly be called "live" to anyone looking at the GitHub repo.
