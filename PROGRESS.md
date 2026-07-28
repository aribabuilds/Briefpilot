# PROGRESS — BriefPilot M1–M30

**Milestones, not dates.** "Day N" in the execution plan = **Milestone N (MN)**. There is no
schedule pressure and no assumption about elapsed time. Source of truth for scope:
`briefpilot-30day-execution-plan.md.pdf` (in `../Briefpilot-decisions/`), governed by `CLAUDE.md`.

**Status legend:** `todo` · `in progress` · `done` · `blocked`

**Rule:** never start a milestone whose dependency isn't done. Critical path is
foundation → upload → OCR with bboxes → extraction → validators → highlight overlay → docs/demo.

---

## Sprint 1 (M1–M7) — "A letter goes in, real text comes out"

| M | Problem / user story | Status | Summary |
|---|----------------------|--------|---------|
| M1 | *As the maintainer,* I can run and verify the whole stack reproducibly, so every later feature stands on a foundation I can trust (and a recruiter can clone). | **done** | Monorepo scaffold, lint/format/type/test toolchain, **CI verified green**, pre-commit hooks, `Makefile` (`make dev`), `docs/adr/` + ADR-0001, backend boots and serves |
| M2 | *As a user,* I can upload a file and watch it process through to a result — so the whole path exists before any real analysis does. | **done** | `POST /api/v1/jobs` (upload) + `GET /api/v1/jobs/{id}` (poll) behind repo/service seam; landing + upload form + result page with live polling and honest states. Async job+poll wired now so the multi-second pipeline slots in without a rewrite. In-memory store (Postgres deferred). Verified end-to-end in-browser; 17 backend tests |
| M3 | *As a user,* I can upload a real photo or PDF of my letter and have its words read with their positions — so later steps get accurate, locatable text. | **done** | Ingestion (pypdfium2 rasterize, page-limit/corrupt guards) + `OcrService` ABC + `TesseractOcrService` producing the **frozen** normalized schema (`schemas/ocr.py`); ADR-0002. Bake-off resolved to Tesseract by §3 (see below). Normalization unit-tested locally; real Tesseract test runs in CI. Pipeline wiring deferred to M5 |
| M4 | *As a user,* I can photograph a slightly skewed or dimly lit letter and still get accurate text — I don't need a perfect flatbed scan. | **done** | `services/preprocess.py`: grayscale → conservative projection-profile deskew (skips trivial/saturated angles) → CLAHE contrast → bounded downscale, toggleable. Transforms unit-tested locally; measured OCR-confidence lift on a 12° skew runs in CI (fail-loud). OpenCV-headless (no system libs). Coords safe — preprocessing precedes OCR; ADR-0002 fractions survive downscale. Pipeline wiring still M5 |
| M5 | *As a user,* when I upload a letter I get back the actual extracted text of *my* document, not a placeholder. | **done** | `document_pipeline.build_document` (rasterize → preprocess → OCR per page) runs in a background thread pool off the request path; job flips to DONE with real text/summary or FAILED with an error. Per-page retry isolates one bad page, but **total failure surfaces** (all pages fail → `DocumentOcrError` → job failed, not a silent empty "done" — caught by running it locally). Thread-safe in-memory repo; OCR timeout. Verified in-browser (failed path renders cleanly); 45 tests, real OCR e2e in CI |
| M6 | *As a user,* if my photo is too poor to read, I'm told to retake it (with tips) instead of being handed silent garbage. | todo | Page-confidence threshold, "retake photo" UX, golden set → 10 letters |
| M7 | *As a user,* the upload→text journey works reliably on my actual phone. | todo | Bug sweep, phone-camera test, retro, demo capture |

## Sprint 2 (M8–M14) — "The pipeline understands the letter"

| M | Problem / user story | Status | Summary |
|---|----------------------|--------|---------|
| M8 | *As a user,* the app recognizes what kind of letter I uploaded (Finanzamt, Krankenkasse, Bußgeld…), so it applies the right handling. | todo | LLM classifier, few-shot per type, "other" fallback, eval vs labeled set |
| M9 | *As a user,* the important parts of my letter are captured in a structured form — each field carrying its confidence and where it came from — so results are trustworthy and traceable. | todo | Pydantic schemas top-4 types + generic; `{value, confidence, source_span}` wrapper |
| M10 | *As a user,* I see the sender, dates, deadlines, amounts and required actions pulled out of my letter, each linked back to the words it came from. | todo | End-to-end extraction, source-span linking, null-not-guess in prompt + parser |
| M11 | *As a user,* I can trust the extracted dates/amounts/§-references because impossible values are caught and flagged, never silently shown as fact. | todo | Date/deadline/legal-ref/amount rules; failures downgrade + flag, never fix |
| M12 | *As a hiring manager,* I can see published per-field accuracy on real letters — the quality is measured, not merely claimed. | todo | Scoring script, scorecard markdown, fast-subset CI job, baseline run |
| M13 | *As a user,* extraction is accurate enough on the common letter types that I can rely on the deadlines it finds. | todo | Measured prompt iterations; per-type few-shots; scope decision point |
| M14 | *As a user,* each field shows an honest confidence signal, so I know what to double-check. | todo | Confidence-tier logic, golden set → 20, retro |

## Sprint 3 (M15–M21) — "A human can use and verify it"

| M | Problem / user story | Status | Summary |
|---|----------------------|--------|---------|
| M15 | *As a user,* I get a plain-English explanation of my letter, grounded only in its own content — so I understand it without jargon and without invented legal advice. | todo | Grounded prompt, readability constraints, advice-phrase linter, disclaimer |
| M16 | *As a user,* I get a deadline-sorted action checklist, and I can tap any unfamiliar German term for a plain definition. | todo | Action derivation with urgency flags; 50-term Amtsdeutsch glossary + popovers |
| M17 | *As a user,* I see one clear results page — summary, explanation, checklist — that works on my phone, with honest loading and error states. | todo | Summary card, explanation, checklist, honest processing states, error/empty states |
| M18 | *As a user,* I can see the original scan of my letter rendered in the app. | todo | Document viewer, coordinate normalization, bbox rendering at any scale |
| M19 | *As a user,* I can tap an extracted field and see exactly where it appears, highlighted in my original letter — proof the AI didn't invent it. | todo | Click field → scroll + highlight, multi-page, low-confidence verify prompts |
| M20 | *As a user,* the full journey keeps working from one release to the next. | todo | Playwright E2E happy path; OCR→extract→explain integration tests |
| M21 | *As a real non-native user,* I can complete the whole journey on my phone without getting confused. | todo | 2 non-native testers on real phones, top-3 friction fixes, screenshots |

## Sprint 4 (M22–M30) — "Ship, harden, and tell the story"

| M | Problem / user story | Status | Summary |
|---|----------------------|--------|---------|
| M22 | *As a user,* I can delete my document in one click and know it's really gone (and auto-purged within 24h) — no account required. | todo | One-click delete verified at storage layer, 24h auto-purge, no accounts |
| M23 | *As a user,* I can read, in plain language, exactly what happens to my data — and it matches what the code actually does. | todo | Plain-language privacy page matching actual behavior; final landing copy |
| M24 | *As a user,* the service stays responsive and safe even under load or abusive input. | todo | Rate limiting, size guards, structured logging, uptime monitor, guardrails |
| M25 | *As a hiring manager,* I can read an honest account of what the system gets wrong and why. | todo | Full eval on 30 golden letters; honest failure analysis; freeze scorecard |
| M26 | *As a hiring manager,* I can understand the architecture and reproduce the project from the README in minutes. | todo | Architecture diagram, portfolio README rewrite, ADR index |
| M27 | *As a hiring manager,* I can watch a 3-minute demo of the full journey without running anything myself. | todo | 3-minute demo video, screenshot set |
| M28 | *As a new user or developer,* I can follow the README on a clean machine and it just works. | todo | Follow README on fresh environment, fix gaps, triage bugs |
| M29 | *As the maintainer,* I can confidently declare the MVP live and monitored. | todo | Full launch checklist, monitor verification |
| M30 | *As the owner,* I can share the finished project and its lessons publicly. | todo | Launch post, `docs/retro.md`, post-MVP Sprint-5 candidates |

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
