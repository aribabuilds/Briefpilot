# PROGRESS — BriefPilot M1–M30

**Milestones, not dates.** "Day N" in the execution plan = **Milestone N (MN)**. There is no
schedule pressure and no assumption about elapsed time. Source of truth for scope:
`briefpilot-30day-execution-plan.md.pdf` (in `../Briefpilot-decisions/`), governed by `CLAUDE.md`.

**Status legend:** `todo` · `in progress` · `done` · `blocked`

**Rule:** never start a milestone whose dependency isn't done. Critical path is
foundation → upload → OCR with bboxes → extraction → validators → highlight overlay → docs/demo.

---

## Sprint 1 (M1–M7) — "A letter goes in, real text comes out"

| M | Objective | Status | Summary |
|---|-----------|--------|---------|
| M1 | Repo + environments | **done** | Monorepo scaffold, lint/format/type/test toolchain, **CI verified green**, pre-commit hooks, `Makefile` (`make dev`), `docs/adr/` + ADR-0001, backend boots and serves |
| M2 | Walking skeleton | **done** | `POST /api/v1/jobs` (upload) + `GET /api/v1/jobs/{id}` (poll) behind repo/service seam; landing + upload form + result page with live polling and honest states. Async job+poll wired now so the multi-second pipeline slots in without a rewrite. In-memory store (Postgres deferred). Verified end-to-end in-browser; 17 backend tests |
| M3 | Real upload + OCR bake-off | **done** | Ingestion (pypdfium2 rasterize, page-limit/corrupt guards) + `OcrService` ABC + `TesseractOcrService` producing the **frozen** normalized schema (`schemas/ocr.py`); ADR-0002. Bake-off resolved to Tesseract by §3 (see below). Normalization unit-tested locally; real Tesseract test runs in CI. Pipeline wiring deferred to M5 |
| M4 | Preprocessing | todo | Deskew, contrast, downscale (OpenCV/Pillow); measured OCR-confidence lift |
| M5 | OCR integration | todo | OCR client wrapper, normalized `{text, page, bbox, confidence}`, multi-page merge, retries |
| M6 | Quality gate + fixtures | todo | Page-confidence threshold, "retake photo" UX, golden set → 10 letters |
| M7 | Sprint-1 close | todo | Bug sweep, phone-camera test, retro, demo capture |

## Sprint 2 (M8–M14) — "The pipeline understands the letter"

| M | Objective | Status | Summary |
|---|-----------|--------|---------|
| M8 | Classification | todo | LLM classifier, few-shot per type, "other" fallback, eval vs labeled set |
| M9 | Extraction schemas | todo | Pydantic schemas top-4 types + generic; `{value, confidence, source_span}` wrapper |
| M10 | Extraction v1 | todo | End-to-end extraction, source-span linking, null-not-guess in prompt + parser |
| M11 | Validator layer | todo | Date/deadline/legal-ref/amount rules; failures downgrade + flag, never fix |
| M12 | Eval harness | todo | Scoring script, scorecard markdown, fast-subset CI job, baseline run |
| M13 | Accuracy iteration | todo | Measured prompt iterations; per-type few-shots; scope decision point |
| M14 | Sprint-2 close | todo | Confidence-tier logic, golden set → 20, retro |

## Sprint 3 (M15–M21) — "A human can use and verify it"

| M | Objective | Status | Summary |
|---|-----------|--------|---------|
| M15 | Explanation engine | todo | Grounded prompt, readability constraints, advice-phrase linter, disclaimer |
| M16 | Checklist + glossary | todo | Action derivation with urgency flags; 50-term Amtsdeutsch glossary + popovers |
| M17 | Results page | todo | Summary card, explanation, checklist, honest processing states, error/empty states |
| M18 | Source-highlight overlay pt.1 | todo | Document viewer, coordinate normalization, bbox rendering at any scale |
| M19 | Overlay pt.2 | todo | Click field → scroll + highlight, multi-page, low-confidence verify prompts |
| M20 | Test hardening | todo | Playwright E2E happy path; OCR→extract→explain integration tests |
| M21 | Sprint-3 close + usability | todo | 2 non-native testers on real phones, top-3 friction fixes, screenshots |

## Sprint 4 (M22–M30) — "Ship, harden, and tell the story"

| M | Objective | Status | Summary |
|---|-----------|--------|---------|
| M22 | Privacy features | todo | One-click delete verified at storage layer, 24h auto-purge, no accounts |
| M23 | Privacy page + landing | todo | Plain-language privacy page matching actual behavior; final landing copy |
| M24 | Production hardening | todo | Rate limiting, size guards, structured logging, uptime monitor, guardrails |
| M25 | Final eval + failure analysis | todo | Full eval on 30 golden letters; honest failure analysis; freeze scorecard |
| M26 | README + architecture | todo | Architecture diagram, portfolio README rewrite, ADR index |
| M27 | Demo assets | todo | 3-minute demo video, screenshot set |
| M28 | Clean-machine test + bug sweep | todo | Follow README on fresh environment, fix gaps, triage bugs |
| M29 | Launch checklist | todo | Full launch checklist, monitor verification |
| M30 | Publish + retrospective | todo | Launch post, `docs/retro.md`, post-MVP Sprint-5 candidates |

---

## Zero-cost adaptations (CLAUDE.md §3 overrides the execution plan)

The execution plan assumes a funded project. `CLAUDE.md` §3 is a **hard rule** and wins where they conflict:

- **M1** — plan says "EU-region deploy target (Hetzner/Fly EU or Vercel fra1) + Sentry EU."
  Adapted: **no hosting is provisioned.** Demo strategy is local (`make dev` / Docker Compose)
  + recorded video + a README a recruiter can follow on a clean machine. A free tier may be
  *proposed* later, never silently provisioned.
- **M3** — plan says bake off Azure Document Intelligence vs Google Vision vs Tesseract.
  Adapted: **Tesseract is the default** for dev, CI, and demo; the paid providers were not
  provisioned or benchmarked (doing so would itself violate §3). The `OcrService` adapter is
  designed so a paid provider is a config/adapter swap later. **ADR-0002** records the decision
  and freezes the coordinate schema.
- **M8+** — LLM must run on a **free tier** (e.g. Gemini Flash) behind the model-agnostic wrapper.
  No paid API calls. See "Known deviations" below.
- **M29** — no paid domain/DNS/VPS. Launch = public repo + video + reproducible local run.

## Known deviations & carried debt

| Item | Impact | Where it gets resolved |
|------|--------|------------------------|
| ~~CI workflow triggers on `main`; repo branch is `master` — CI has never run~~ | **RESOLVED.** Branch renamed to `main` (D1); `ci.yml` needed no edit. First run failed (black + mypy in `core/logging.py`); fixed in `45a8b59`. **Run #3 green: Frontend 47s, Backend 31s** | M1 ✅ |
| `AIService` ships only **OpenAI + Azure OpenAI** adapters — both paid | Violates §3 zero-cost mandate if used; built ahead of its milestone | Default flipped off paid in M1; free-tier adapter lands in M8 where the LLM is actually needed |
| Wrapper is named `AIService`; CLAUDE.md §4 calls it `llm_client` | Naming drift vs. the spec | M8 (rename or ADR justifying the name) |
| ~~No `pre-commit` hooks~~ | **RESOLVED.** `.pre-commit-config.yaml`, all hooks verified passing on the full tree | M1 ✅ |
| ~~No `docs/adr/` directory~~ | **RESOLVED.** `docs/adr/` + index + ADR-0001 (local-first zero-cost strategy) | M1 ✅ |
| ~~No `LEARNING.md`~~ | **RESOLVED.** M1 review with 4 decisions, 3 review questions, teach-back | M1 ✅ |
| ~~Frontend source never prettier-formatted~~ | **RESOLVED.** CI ran `lint` + `build`, which both pass on unformatted code; `format:check` added to CI and 3 files reformatted | M1 ✅ |
| `make` not installed on the owner's Windows machine | `make dev` won't run locally until `choco install make`; Makefile targets are thin wrappers, documented in README | Owner's call |
| ~~Backend never executed locally~~ | **RESOLVED.** Full backend job now runs locally (Python 3.14 venv) and in CI: ruff, black, isort, mypy strict all clean; **9 tests pass**, incl. the `AIService` factory tests. Note local 3.14 vs project target 3.13 — Docker/CI remain the source of truth | M1 ✅ |
| Existing commits don't follow conventional-commit format | §5.7 | Going forward only; history not rewritten |
