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
| M6 | *As a user,* if my photo is too poor to read, I'm told to retake it (with tips) instead of being handed silent garbage. | **done** | `services/quality.py` (pure `assess_quality`: word-count + mean-confidence thresholds) wired into `JobService` as a new terminal status `low_quality` — distinct from `failed` (OCR ran, output just isn't trustworthy). `RetakePrompt` shows confidence + photo tips and **deliberately withholds the OCR text**. Verified live (backend confirms status; browser renders the prompt with no console errors and no leaked text) via a temporary dependency-override server, since real low-confidence output needs a real bad photo. `eval/golden/` scaffolded (manifest + label format + README); **0 real letters collected yet** — that's the owner's parallel task, not fabricated. 60 tests pass locally |
| M7 | *As a user,* the upload→text journey works reliably on my actual phone. | **done** (Claude's half) | Bug sweep (`.gitattributes`, stale README intro, stale Known Deviations rows all fixed); bad-photo quality-gate test proven against real Tesseract in CI; LAN phone-test instructions in README; demo shot list + LinkedIn draft written. **Owner's half still open:** the phone test itself, the screen recording, publishing, and golden-letter collection — see Sprint-1 review below |

### Sprint-1 review

Scored against the plan's actual Sprint-1 goal: *"de-risk the single scariest dependency — OCR
quality on real-world photos — in week one"* via *"live walking skeleton + upload + preprocessing
+ OCR with bounding boxes + quality gate."*

| DoD item | Status | Note |
|---|---|---|
| Engineering objective met (skeleton + upload + preprocessing + OCR w/ bboxes + quality gate) | ✅ | M1–M6, all CI-verified |
| CI green | ✅ | Verified repeatedly; M6 even caught and fixed a real cross-milestone regression (see LEARNING.md) |
| Skeleton deployed | ❌ **by design** | ADR-0001 — zero-cost mandate; local `make dev` is the deploy target, not a live URL |
| 10 golden letters collected | ❌ **not started** | `eval/golden/` scaffolded (M6); 0 real letters — deliberately never Claude's task |
| Upload works on a real phone | ⏳ **untested** | README now documents the LAN-IP config needed (M7); the test itself needs the owner's phone |
| OCR JSON includes bboxes | ✅ | Frozen since M3 (ADR-0002): every `OcrWord` carries a fractional `BBox` |
| Quality gate triggers on a deliberately bad photo | ✅ | Proven against **real Tesseract** in CI as of M7 (previously only proven against a synthetic confidence dict) |

**Bottom line:** everything within Claude's control is done and verified. What's open —
golden letters, the phone test, the demo recording, the LinkedIn post — was always the owner's
half of Sprint 1, not slippage.

**Retro questions** (from the execution plan, for the owner — not graded, just asked):
1. Was the OCR bake-off decisive? (Note: it was resolved by the zero-cost mandate rather than a
   head-to-head benchmark — see ADR-0002. Does that feel like a real answer or a dodge?)
2. Is the 6–8h/day pace real, now that milestones are decoupled from calendar days?
3. What surprised you about real letters, once golden-set collection starts?

## Sprint 2 (M8–M14) — "The pipeline understands the letter"

| M | Problem / user story | Status | Summary |
|---|----------------------|--------|---------|
| M8 | *As a user,* the app recognizes what kind of letter I uploaded (Finanzamt, Krankenkasse, Bußgeld…), so it applies the right handling. | **done** | `classify_document` added to the `AIService` interface (all 3 adapters); new `GeminiService` (free tier) is now the **default** provider — resolves the paid-default deviation from M1. Response parsing is a pure, provider-shared function with an `other` fallback on any malformed output (never a guessed type). Wired into `JobService`: runs only after the quality gate passes, degrades to `doc_type: null` on any failure (no key, network, provider outage) without failing the job. ADR-0003. "Eval vs labeled set" deferred — still 0 golden letters, not fabricated. 77 tests pass locally |
| M9 | *As a user,* the important parts of my letter are captured in a structured form — each field carrying its confidence and where it came from — so results are trustworthy and traceable. | **done** | `LetterExtraction` — **one common schema for all 8 types**, not per-type (ADR-0004; deviates deliberately from the plan's literal "top-4 + generic" — no real letters yet to justify guessing per-type differences). Generic `ExtractedField[T]` wrapper (PEP 695 syntax; pydantic floor raised to 2.11) carries `{value, confidence, source_span}`; `source_span` reuses the frozen M3 `BBox`. Replaced the stale M1 `DocumentExtractionResult` placeholder (zero real callers) with this real contract. Shared, provider-agnostic parser never raises — malformed/missing fields degrade to null per-field. Prompt scaffolding only; wiring into `JobService` + real source-span linking is M10. 88 tests pass locally |
| M10 | *As a user,* I see the sender, dates, deadlines, amounts and required actions pulled out of my letter, each linked back to the words it came from. | **done** | `LetterExtraction` goes live: `JobService` runs extraction as a second best-effort step (independent of classification), then `link_source_spans` matches each value back to real OCR words. Matching splits into candidate generators (German date formats, comma/period amounts) + a pure word-window matcher — unlinkable values get their confidence **capped, not zeroed** (an ungrounded value must not look as trustworthy as a verified one). Verified live (both verified ✓ and unverified fields render correctly); CI-gated test proves linking finds real bboxes against real Tesseract output. 118 tests pass locally (6 skip without Tesseract) |
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
- **M8+** — LLM must run on a **free tier**. **Resolved at M8**: `GeminiService` (Gemini Flash
  free tier) is now the default `AI_PROVIDER`; OpenAI/Azure remain opt-in only. ADR-0003.
- **M29** — no paid domain/DNS/VPS. Launch = public repo + video + reproducible local run.

## Known deviations & carried debt

| Item | Impact | Where it gets resolved |
|------|--------|------------------------|
| ~~CI workflow triggers on `main`; repo branch is `master` — CI has never run~~ | **RESOLVED.** Branch renamed to `main` (D1); `ci.yml` needed no edit. First run failed (black + mypy in `core/logging.py`); fixed in `45a8b59`. **Run #3 green: Frontend 47s, Backend 31s** | M1 ✅ |
| ~~`AIService` ships only **OpenAI + Azure OpenAI** adapters — both paid~~ | **RESOLVED.** `GeminiService` added; `AI_PROVIDER` now defaults to `gemini` (free tier). Paid providers are opt-in only | M8 ✅ (ADR-0003) |
| ~~Wrapper is named `AIService`; CLAUDE.md §4 calls it `llm_client`~~ | **RESOLVED.** Kept `AIService`: by M8 it's a 3-operation, 3-provider capability interface, not a single-call client wrapper. ADR-0003 documents the reasoning | M8 ✅ (ADR-0003) |
| `GEMINI_API_KEY` not yet obtained | Classification degrades to `doc_type: null` (null-not-guess) until a free key is added to `backend/.env` — get one at https://aistudio.google.com/apikey | Owner — no code change needed once added |
| ~~No `pre-commit` hooks~~ | **RESOLVED.** `.pre-commit-config.yaml`, all hooks verified passing on the full tree | M1 ✅ |
| ~~No `docs/adr/` directory~~ | **RESOLVED.** `docs/adr/` + index + ADR-0001 (local-first zero-cost strategy) | M1 ✅ |
| ~~No `LEARNING.md`~~ | **RESOLVED.** M1 review with 4 decisions, 3 review questions, teach-back | M1 ✅ |
| ~~Frontend source never prettier-formatted~~ | **RESOLVED.** CI ran `lint` + `build`, which both pass on unformatted code; `format:check` added to CI and 3 files reformatted | M1 ✅ |
| `make` not installed on the owner's Windows machine | `make dev` won't run locally until `choco install make`; Makefile targets are thin wrappers, documented in README | Owner's call |
| ~~Backend never executed locally~~ | **RESOLVED.** Full backend job now runs locally (Python 3.14 venv) and in CI: ruff, black, isort, mypy strict all clean; **9 tests pass**, incl. the `AIService` factory tests. Note local 3.14 vs project target 3.13 — Docker/CI remain the source of truth | M1 ✅ |
| ~~Existing commits don't follow conventional-commit format~~ | **HOLDING.** Verified: every commit from M2 onward (`feat:`/`fix:`/`test:`/`docs:`/`chore:`) has followed the convention; history before that isn't rewritten | Ongoing, self-verified at M7 |
| ~~Every commit warns "LF will be replaced by CRLF"~~ | **RESOLVED.** Flagged after M2, never actually fixed until this bug sweep caught it. Added `.gitattributes` (`* text=auto eol=lf`); verified the warning no longer fires on `git add` | M7 ✅ |
| Sprint-1 DoD item "10 golden letters collected" — **0 collected** | `eval/golden/` scaffold exists (M6) but is empty; this was deliberately never Claude's task (fabricating letters would produce a dishonest scorecard) | Owner, ongoing — not blocking Sprint 2 |
| Sprint-1 DoD item "upload works on a real phone" — **never tested** | No phone + LAN test has been run; `NEXT_PUBLIC_API_URL` bakes `localhost` at build time, which breaks from an actual phone unless overridden — documented in README (M7) | Owner — see README "Testing on a real phone" |
