# LEARNING — BriefPilot

Milestone reviews: decisions made, what was rejected, and what to be able to defend in an
interview. Newest milestone at the bottom.

---

## M1 — Repo + environments *(in progress)*

### Decisions log

#### D1 — Rename the default branch `master` → `main`, now rather than later

**What.** Renamed the local branch, pushed `main` to `origin`, and set it as the repository's
default. `.github/workflows/ci.yml` needed **no edit** — it already targeted `main`; the branch
was the mismatched side.

**Why now.** The cost of renaming a default branch is not fixed — it grows with how many things
point at the old name. Today that count is effectively zero:

- one contributor, no collaborators, no forks, no clones to migrate
- zero open pull requests to retarget
- no CI history to orphan, no branch protection rules, no deploy webhooks with branch filters
- no README badges, no external documentation, no published links into the repo

So the blast radius today is: one `git branch -m`, one push, one settings change. Minutes.

**Why it would be risky later.** Every artifact this project is *designed* to produce points into
the repo by URL, and most of them hard-code the branch name:

- deep links of the form `github.com/…/blob/master/…` in the portfolio README (M26)
- `raw.githubusercontent.com/…/master/…` links — these are the ones that break hardest, because
  GitHub's rename redirects cover many web URLs but **not** raw content URLs
- the LinkedIn posts scheduled at M7, M14, M21 and M30, which are recruiter-facing and permanent
- the published eval scorecard (M12, M25) and ADR index (M26), which cross-reference paths
- CI badge URLs once CI is actually producing runs

A rename after M26 means the exact artifacts built to impress a hiring manager start 404-ing,
and you cannot edit a LinkedIn post's dead link out of someone's memory. The general principle:
**do breaking changes when the blast radius is smallest, because the cost of change rises
monotonically with adoption.** Recognising that curve *before* it bites is most of what
separates "developer" from "engineer."

**What was rejected.** Pointing the workflow at `master` instead (a one-line edit, zero risk
today). Rejected because it locks in the older convention permanently for a repository whose
entire purpose is to be read by German engineering teams — where `main` is now the near-universal
default — and it would leave a papered-over inconsistency rather than a resolved one. The
cheaper fix today would have been the more expensive one at M26.

**What a German tech interviewer might ask.**
- *"You renamed a default branch. Walk me through the blast radius — what breaks, and for whom?"*
  (They are testing whether you think about consumers of your change, not just the change.)
- *"Why did you do it at that point in the project rather than at the end?"*
  (They want to hear the cost-of-change curve, and evidence you sequence risky work deliberately.)
- *"What would you have done differently if the repo already had five contributors and an
  active deployment?"* (Answer: coordinate — announce, rename, provide the two-line
  `git branch -m` migration snippet, update CI and deploy filters in the same change, and keep
  the old branch alive briefly as a redirect. The decision flips from "just do it" to "plan it.")

#### D2 — The CI mismatch was a *silent* failure, and that is the real lesson

**What.** `ci.yml` triggered on `branches: [main]` while the only branch was `master`. GitHub
Actions does not warn when a workflow's trigger matches nothing — it simply never runs. Two
commits were pushed believing lint, type-checks and tests were being enforced. **Nothing had
ever executed.**

**Why it matters more than the bug.** The pipeline was not red. It was *absent* — and absence
looks exactly like success on a repository page. Every previous claim in this project that
"lint and tests pass" was unfalsifiable. This is the failure mode behind a whole class of
production incidents: the alert that was never wired, the health check pointing at a stale
endpoint, the backup job whose cron silently stopped firing. The defence is the same in all
cases: **treat missing signal as failure, not as success** — assert that the thing ran, don't
just check that it didn't complain.

**What a German tech interviewer might ask.**
- *"How would you detect a CI job that silently stopped running?"* (Required status checks on
  the branch, so a merge is blocked when the check is absent rather than passing; plus alerting
  on stale/missing runs.)
- *"What's the difference between a green build and a build you trust?"*

#### D3 — Pre-commit hooks format and lint only; mypy, eslint and pytest stay in CI

**What.** `.pre-commit-config.yaml` runs hygiene checks, ruff, black, isort and prettier.
It deliberately does **not** run mypy, eslint or pytest.

**Why.** A commit hook competes with the developer's attention every single commit. Hooks that
take thirty seconds get bypassed with `git commit --no-verify`, and a bypassed hook protects
nothing while still appearing in the repo as though it does — the same "looks protected, isn't"
failure as D2. So the split is by *cost*, not by importance: sub-second mechanical fixes run
locally; anything slow or requiring a full dependency graph runs in CI, where waiting is free
because it happens without you.

**What was rejected.** Putting mypy in pre-commit via `mirrors-mypy`. It needs
`additional_dependencies` mirroring the whole runtime dependency list, which then silently
drifts from `requirements.txt` — a second source of truth for dependencies, checking types
against versions you don't actually run.

**Two things this decision cost, discovered by running it.** Both are recorded because they are
the kind of detail that only shows up on execution:

1. The generic `end-of-file-fixer` hook rewrote 13 exported SVG brand assets. Vendored design
   artifacts are not source; formatting them creates noise and can corrupt exports. Fixed with
   a top-level `exclude: ^BriefPilot-Logo/`.
2. Prettier could not resolve `prettier-plugin-tailwindcss` in an isolated hook environment,
   because prettier v3 resolves plugins relative to the working directory. The hook would have
   *passed* while silently skipping Tailwind class sorting — then fought `npm run format` over
   the same files forever. Fixed by invoking the frontend's own `npm run format`, so there is
   exactly one formatter with one config.

**What a German tech interviewer might ask.**
- *"Where do you draw the line between a pre-commit hook and a CI check?"*
- *"Your hook and your npm script format the same files. How do you stop them disagreeing?"*
  (One tool, one config, invoked the same way from both places.)

#### D4 — CI ran `lint` and `build` but never `format:check`, so formatting drifted unchecked

**What.** The frontend CI job ran ESLint and `next build`. Both pass happily on unformatted
code. The first time `prettier --check` was ever executed, it reformatted three source files —
including the landing page — meaning the frontend had *never* matched its own committed style
config. `npm run format:check` is now a CI step.

**Why it matters.** This is D2's lesson in a second costume, and that repetition is the point.
A quality gate only enforces what it actually executes. `package.json` declared a `format:check`
script; `.prettierrc.json` declared the rules; a reader would reasonably conclude formatting was
enforced. Nothing ran it. **Configuration is not enforcement** — the check has to be wired into
a pipeline that fails.

**What a German tech interviewer might ask.**
- *"How would you audit whether your CI actually enforces everything your repo claims to?"*
  (Walk the declared scripts and configs and ask, for each, which pipeline step executes it —
  then break something deliberately and confirm the pipeline goes red.)

---

### Review questions

Answer these before M2 starts. Take them seriously — I will grade honestly.

1. **Read the code.** Open `backend/app/services/ai/factory.py`. `get_ai_service()` is decorated
   with `@lru_cache` while `build_ai_service(settings)` is not. Why is the split there, and what
   would break in the tests if `build_ai_service` were the cached one?

2. **Design.** Suppose we move `AIService` out of `services/ai/` and have each API router
   instantiate `OpenAIService` directly where it needs one. Name three concrete things that get
   harder — and be specific about which of them is worst when we add the Gemini adapter at M8.

3. **Engineering practice.** CI now runs `black --check` rather than `black`. Why is
   `--check` the right thing in CI, when the pre-commit hook runs the *rewriting* version of the
   same tool? What would go wrong if CI auto-formatted and pushed the result?

### Teach-back

Explain in 60 seconds, to someone who is not an engineer:

> **"Our tests were passing for two weeks. They had never run once."**

Cover: how a pipeline can be absent rather than failing, why absence looks identical to success
on a dashboard, and the one change that makes the difference visible. If you can land why
*"no news is good news"* is a dangerous default in engineering, you have it — that is the
transferable idea, and it is worth a LinkedIn post.

---

## M2 — Walking skeleton *(done)*

### Decisions log

#### D5 — Async job + polling, not a synchronous upload-returns-result stub

**What.** `POST /jobs` returns a job id immediately; the client polls `GET /jobs/{id}` until
the status flips to `done`. Even though the M2 stub has nothing to compute, the contract is
asynchronous from day one.

**Why.** The eventual pipeline — OCR, classify, extract, validate, explain — is inherently
multi-second and cannot answer within one HTTP request without holding a connection open and
timing out behind proxies. Choosing the async contract now, while it is a stub, means M3–M5
slot real work into an existing shape. The alternative (synchronous now, async later) is the
more expensive path: it rewrites the API contract *and* the frontend's data flow *and* the
tests, after other code already depends on the synchronous version. The general principle:
**pay for the load-bearing shape of an interface early, when nothing depends on it yet.**

**What was rejected.** Synchronous `POST /jobs` returning the result inline. Less code in M2,
but a guaranteed rewrite the moment OCR (seconds) lands.

**Interview angle.** *"When would you choose an async job API over a synchronous endpoint?"*
The trigger is work that exceeds a request budget (roughly >1–2s, or unbounded) — OCR + LLM is
firmly there. Follow-up they may push on: polling vs webhooks vs SSE/WebSockets. Polling is the
right MVP call — trivial to build, no connection state, fine at demo scale; the cost is latency
granularity and wasted requests, which a job queue + push would fix at real scale.

#### D6 — Completion is a lazily-evaluated, clock-injectable state transition

**What.** The stub job has no background worker. `get_job` computes whether enough time has
elapsed and transitions `processing → done` on read, using an injected `clock` callable.

**Why.** It keeps the stub honest (the job really does report "processing" then "done") with no
threads or `asyncio` timers, and — because the clock is injected — the state machine is
unit-tested deterministically with a fake clock, no `sleep`, no flake. When the real pipeline
lands, the elapsed-time check becomes "is the pipeline finished"; the poll-until-done contract
is unchanged.

**Interview angle.** *"How do you test time-dependent logic without making the test slow or
flaky?"* Inject the clock (dependency injection for `now()`); never call the wall clock directly
in logic you want to test.

### Review questions

1. **Read the code.** In `services/job_service.py`, `get_job` writes the completed job back to
   the repository (`update`) when it transitions. Why persist it, rather than just returning the
   computed `done` state each read? What breaks in M5 (real pipeline) if we *don't* persist?
2. **Design.** The in-memory repo is a process-wide singleton via `@lru_cache`. Name what breaks
   the moment we run two backend replicas — and why the `JobRepository` interface means the fix
   is small.
3. **Practice.** The router validates content-type and size and returns 415/413 before creating
   a job. Why enforce those at the API boundary rather than inside `JobService`?

### Teach-back

> **"We built the slow, async version of the API before we had anything slow to run."**
Explain why paying for the async job+poll shape up front was cheaper than the synchronous
shortcut — in terms of what depends on an interface once it exists.

---

## M3 — Real ingestion + OCR adapter *(done)*

### Decisions log

#### D7 — Bounding boxes stored as page fractions [0, 1], not pixels (frozen: ADR-0002)

**What.** The normalized OCR schema stores every box as a fraction of the page, not pixel
coordinates. Confidence likewise normalized to [0, 1] from Tesseract's 0–100.

**Why.** This is a "must not change" contract — the overlay and all eval fixtures build on it —
so resolution-independence matters more than convenience. Pixels couple every stored box to the
raster DPI: the moment M4 preprocessing downscales a page, or the frontend renders at a
different size, pixel boxes are wrong. Fractions survive any rescale — the overlay just
multiplies by whatever size it draws at. Deciding this *before* fixtures exist is the whole
point; changing it after M12 would invalidate the golden set.

**Interview angle.** *"Why normalize coordinates instead of storing what the OCR engine gave
you?"* Provider- and resolution-independence at a stable interface. Ties to the adapter pattern:
the internal schema is decoupled from any one provider's native format.

#### D8 — OCR behind an interface; testing splits by what needs the binary

**What.** `OcrService` ABC + `TesseractOcrService` (the only importer of `pytesseract`). The
pixel→fraction normalization is a pure function unit-tested against a synthetic Tesseract dict;
the live engine runs only in a CI-gated integration test, which is guarded to **fail loudly in
CI** rather than skip.

**Why.** Tesseract isn't on the dev machine, so most of the value — the normalization logic — is
tested with no binary at all. The one thing that genuinely needs the engine is isolated and
pushed to CI, which is declared the source of truth for OCR (ADR-0002). The fail-loud-in-CI
guard is D2's lesson applied directly: a test that skips in CI is "green but never ran."

**Interview angle.** *"How do you test code that depends on an external binary or service?"*
Separate the pure logic (test everywhere) from the integration edge (test where the dependency
lives); never let the integration test silently skip in the environment that's supposed to run
it.

### Review questions

1. **Read the code.** `_normalize` is a module-level function taking a plain dict, not a method
   on `TesseractOcrService`. Why does that structure make it easier to test — and what did it let
   the unit tests avoid constructing?
2. **Design.** We chose pypdfium2 over PyMuPDF partly on licensing (AGPL). For a public portfolio
   whose source is already open, does the AGPL concern actually apply? Argue both sides, then say
   what you'd choose and why.
3. **Practice.** ADR-0002 calls the coordinate schema "frozen." What concretely goes wrong at M12
   (eval harness) and M18 (overlay) if we quietly change `BBox` from fractions to pixels later?

### Teach-back

> **"We store where a word is as a percentage of the page, not in pixels."**
Explain, to a non-engineer, why that one choice means a highlight still lands on the right word
after the image is resized — and why we had to lock it in before building anything on top.

---

## M4 — Image preprocessing *(done)*

### Decisions log

#### D9 — Deskew by projection-profile maximization, not minAreaRect

**What.** Skew is estimated by rotating the thresholded page through candidate angles and picking
the one that maximizes the variance of the horizontal projection (row sums). The obvious
first choice — `cv2.minAreaRect` on the text pixel cloud — was prototyped first and **rejected
on evidence**: it returned −90°, −84°, −77° for true skews of 0°, 5°, 12°. Its angle is
ambiguous for a block wider than it is tall, which is exactly what a page of text is.

**Why it matters.** At the true angle, text rows line up into sharp horizontal bands, so the
row-projection has high peak-to-trough variance; off-angle, the bands smear and variance drops.
Maximizing that variance is a direct, robust signal. The prototype recovered every test angle
exactly. The lesson is process, not trig: **prototype the risky primitive against known inputs
before building on it** — a plausible-looking library call was silently wrong, and only a
ground-truth check caught it.

**Interview angle.** *"How would you detect and correct document skew?"* Name projection-profile
or Hough-line approaches, and be ready to say why the naive bounding-box angle fails on text.

#### D10 — Conservative correction: never rotate on a guess

**What.** Deskew skips two cases: a sub-0.5° estimate (nothing worth resampling for) and an
estimate that saturates near the ±search boundary (the true skew is outside the reliable window,
so the number is untrustworthy). It corrects only in the confident middle band.

**Why.** A preprocessing step that *degrades* some inputs is worse than one that occasionally
does nothing — it introduces a silent failure mode with no error. Resampling a page that was
already straight adds blur; "correcting" a 30° estimate the algorithm can't actually resolve
half-rotates it into something OCR reads worse. The safe default is identity. Same instinct as
the validators to come (M11): when unsure, flag/skip, never silently "fix".

**Interview angle.** *"Your preprocessing helps most inputs but hurts a few — ship it?"* No: the
regression is invisible (no error, just worse accuracy on some docs). Gate the transform to the
regime where you trust it; make doing nothing the fallback.

### Review questions

1. **Read the code.** `estimate_skew_angle` thresholds with `THRESH_BINARY_INV | THRESH_OTSU`
   before scoring. Why invert, and why Otsu rather than a fixed threshold like 127?
2. **Design.** The pipeline is grayscale → deskew → CLAHE → downscale. What breaks or degrades
   if we move downscale *before* deskew? (Think about the projection search and resampling.)
3. **Practice.** The OCR-lift test asserts `preprocessed > raw` on a 12° page but can't run on the
   dev machine. Why is 12° chosen specifically — what would go wrong in CI at 3°, and at 20°?

### Teach-back

> **"We tried the obvious computer-vision function first, and it was confidently wrong."**
Explain how a plausible library call (minAreaRect) gave garbage angles, how a ground-truth
prototype caught it in minutes, and why that check came *before* writing the real module.

---

## M5 — OCR integration (stub becomes real) *(done)*

### Decisions log

#### D11 — Real work runs once in the background, not lazily on every poll

**What.** M2's stub "completed" a job by computing elapsed time on each read (D6). Real OCR
can't work that way — it must run exactly once, off the request path. `create_job` now submits
the pipeline to a thread pool; the worker updates the job to DONE (with the document) or FAILED
(with an error) when it finishes. The clock-driven stub transition is gone.

**Why.** OCR takes seconds and has side effects (CPU, an external binary) — recomputing it per
poll would be absurd and non-idempotent. Moving it off the request path is also what keeps the
async job contract (D5) honest: the HTTP request returns immediately, the work happens
elsewhere. The executor is injected behind a one-method `Executor` protocol, so tests pass a
synchronous stand-in and job completion stays deterministic — no `sleep`, no thread races in the
test suite.

**Interview angle.** *"Where does the OCR actually run, and what happens to the request while it
runs?"* Background worker; request returns a job id immediately; client polls. Follow-up: this
in-process thread pool is fine for demo scale but doesn't survive a restart or scale across
replicas — a durable queue (the BACKLOG item) is the production answer.

#### D12 — Resilience must tell a bad page from a broken engine (caught by running it)

**What.** The per-page retry-then-empty logic was meant so one unreadable page doesn't sink a
ten-page letter. But it caught *every* exception — so with Tesseract entirely absent, all pages
"failed" into empty results and the job reported **DONE with zero words**. Uploading a valid PDF
locally surfaced it immediately: a totally broken OCR engine looked like success.

**Why it matters.** This is D2's silent-failure lesson biting my *own* resilience code. The fix
distinguishes scope: a page that raises is a failure; a page that returns zero words *without*
raising is legitimately blank. If **every** page fails, that's systemic (dead engine, missing
language pack), and the pipeline raises `DocumentOcrError` so the job fails visibly — while
partial failure still degrades gracefully. The tell: resilience that can't fail is not
resilience, it's a mute button.

**What a German interviewer might ask.**
- *"Your pipeline is resilient to a bad page. How do you avoid that resilience hiding a total
  outage?"* (Distinguish partial from total failure; a floor below which you stop coping and
  start alerting.)
- *"How did you find this?"* (Ran it end-to-end on a real input, not just green unit tests — the
  unit tests were happily green because they injected a *working* fake OCR.)

### Review questions

1. **Read the code.** `_extract_with_retry` returns `tuple[OcrPage, bool]` instead of just an
   `OcrPage`. Why is that boolean load-bearing — what could the caller *not* decide without it?
2. **Design.** The `Executor` is a one-method `Protocol`, and tests inject a synchronous version.
   What specifically would become flaky or slow if tests used the real `ThreadPoolExecutor`
   instead?
3. **Practice.** The in-memory repo got a `threading.Lock` in this milestone but not before.
   What exactly changed in M5 that made the lock necessary, and what's the failure it prevents?

### Teach-back

> **"Our error-handling was so forgiving it hid a total outage."**
Explain how catch-everything resilience turned a completely missing OCR engine into a
zero-word "success", and the one distinction (a page that *failed* vs a page that was *blank*)
that fixed it.

---

## M6 — OCR quality gate + retake UX *(done)*

### Decisions log

#### D13 — A third terminal status, not a flag on `failed` or `done`

**What.** `JobStatus` gained `low_quality`, sitting between `done` and `failed`. It's not "failed
with a note" or "done with a warning" — it's its own terminal state, with its own frontend branch
that renders `RetakePrompt` instead of either the result view or the error view.

**Why.** `failed` means the pipeline itself broke (D12's territory — a dead engine, a corrupt
file). `low_quality` means the pipeline worked exactly as designed and still produced output too
unreliable to act on. Conflating them would blur two different remediations: a `failed` job is an
engineering problem (check logs, maybe retry); a `low_quality` job is a user problem (retake the
photo). A shared status with a flag would make the frontend branch on two things at once instead
of one; three clean terminal states is easier to reason about than two states plus a modifier.

**Interview angle.** *"Why not just add a `quality_ok: bool` field to the done result?"* Because
the two failure modes need different UI entirely (retry-with-tips vs. generic error), and a
boolean flag invites the frontend to almost-handle it — check the flag in one place, forget it in
another. A distinct enum value can't be silently ignored the same way; TypeScript's
discriminated union forces every render branch to exist.

#### D14 — Withhold the text entirely; no "low confidence, shown anyway" affordance

**What.** When quality fails, the frontend never renders `result.text`, even faded or behind a
warning banner. `RetakePrompt` shows only the confidence number and word count — never the
garbled OCR output itself.

**Why.** This project's whole trust proposition (`CLAUDE.md` §1, §5) is that extracted content is
provably grounded in the source. Showing "confidence: 20%, but here's what we think it says"
trains the user to treat low-confidence garbage as provisionally true — the opposite of the
trust the source-highlight overlay (M18) is built to earn. It's the same principle as D10's
conservative deskew and D12's fail-loud OCR: when you don't trust the output, don't hand it over
with a disclaimer attached and call that honest. A disclaimer is not a substitute for withholding.

**What was rejected.** A "show anyway" toggle. Logged to BACKLOG as a Nice-to-Have, not built now
— it's real user value (some blurry photos are still readable to a human even at low OCR
confidence) but it directly cuts against the trust principle above, so it needs deliberate
product judgment later, not a quick default now.

**Interview angle.** *"Isn't hiding the data paternalistic? What if the user wants to see it
anyway?"* Good challenge — the honest answer is it's a deliberate trust trade-off for an MVP
whose central claim is "we don't show you things we can't back up," not a technical limitation.
A future "show anyway, unverified" mode is a legitimate feature; it just isn't the safe default.

#### D15 — Golden-set scaffold ships with the format, not with data

**What.** `eval/golden/` got a manifest schema, a per-document label format, and a README
explaining how to collect and redact a real letter — with zero letters in it.

**Why.** The eval suite (M12) is only as honest as its fixtures. Writing plausible-looking fake
letters to hit a milestone checkbox would produce a scorecard that measures nothing real — worse
than no scorecard, because it *looks* rigorous. The format needed to exist now so collection can
start in parallel without blocking on M12; the data itself is explicitly out of scope for an AI
pair to generate.

**Interview angle.** *"Why not generate synthetic test letters to unblock testing sooner?"*
Synthetic data is fine for unit tests of the pipeline mechanics (that's exactly what
`test_document_pipeline.py` and `test_quality.py` already do). It's the wrong tool for an eval
suite whose entire purpose is measuring real-world accuracy — synthetic fixtures silently
optimize for themselves.

### Review questions

1. **Read the code.** `assess_quality` checks `word_count == 0` before computing `mean_confidence`.
   What would happen — concretely, what Python error — if that check came after instead?
2. **Design.** `min_word_count` and `min_mean_confidence` are both hard cutoffs. Name one real
   photo scenario where a document could reasonably pass one threshold and fail the other, and say
   which failure mode (too few words vs. too low confidence) is the more dangerous one to get wrong.
3. **Practice.** The low-quality path was verified live using a script that overrides
   `get_job_service` on the real FastAPI app and runs it under real `uvicorn` — not `TestClient`.
   Why does `app.dependency_overrides` work the same way there, and what does that tell you about
   how FastAPI's dependency injection is actually implemented?

### Teach-back

> **"We show you the confidence score, but never the text it's attached to, if it's too low to trust."**
Explain why "low confidence, shown anyway" would quietly undermine the one thing this whole
project is trying to prove — that what you see is what the letter actually says.

### Post-merge fix: M6 broke M5's own CI test

**What happened.** `9127319` (the M6 commit) passed every local check — ruff, black, isort,
mypy, and 53 passed/4 skipped in pytest — and still went red in CI. `pytest` was the only failed
step; ruff/black/isort/mypy all stayed green. The failure was in `test_pipeline_e2e.py` (M5's
real-OCR end-to-end test), which only executes for real in CI, exactly as designed.

**Root cause.** M6 added a third terminal `JobStatus`, `LOW_QUALITY`, with a default
`min_word_count` of 5. M5's e2e fixture text was `"Finanzamt Muenchen"` — **two words** — so the
real pipeline correctly routed it to `LOW_QUALITY`, not `DONE`. But `_poll_until_terminal` only
recognized `DONE` and `FAILED` as terminal, so it polled for the full 30-second timeout and then
raised a generic "job did not finish" error, with no hint that the real cause was one test's
fixture violating another feature's new threshold.

**Why it matters.** This is D2's family of bugs from the *opposite* direction: not a check that
silently didn't run, but a check that ran, was right, and exposed an implicit coupling my local
suite couldn't see — because the OCR-dependent tests are exactly the ones that skip locally. CI
was not being paranoid; it was the only place this class of regression *could* be caught, which
is the whole reason M3's fail-loud-in-CI guard exists. It's also a concrete argument for running
**every** CI-gated integration test whenever a feature changes shared state (`JobStatus` here),
not just the tests that obviously touch the new code.

**Fix.** Gave the e2e fixture enough words to clear the new threshold with margin, and added
`LOW_QUALITY` to the terminal-status set so a *future* regression fails fast with a clear
assertion message instead of a 30-second timeout and a guess.

**Interview angle.** *"You just told me CI caught something local tests couldn't. Doesn't that
mean your test suite has a blind spot?"* Yes, deliberately: the OCR-dependent tests are the
priciest and least portable (they need a system binary), so they're scoped to CI on purpose (D8).
The trade-off is real — this exact failure mode — and the mitigation isn't "run everything
everywhere," it's "know precisely which tests only run in CI, and treat CI as the actual gate for
that code, not a formality after local tests pass."

---

## M7 — Sprint-1 close *(done)*

### Decisions log

#### D17 — A systematic bug sweep found a fix that had been "flagged" twice and actioned zero times

**What.** The `.gitattributes` CRLF fix was mentioned as a to-do after M2, then again after M5 —
and never actually written, because it never blocked anything urgent enough to force the issue.
It only got fixed now because M7's bug sweep explicitly asked "what's been noted but not done?"
rather than only checking "does everything currently pass?"

**Why it matters.** A TODO mentioned in passing is not the same as a TODO tracked somewhere it
will be looked at again. Nothing in this repo's process forced a revisit — it lived only in prior
chat turns, which is exactly the kind of state that survives a compaction or a session boundary
by accident, not by design. The fix itself: `* text=auto eol=lf` in `.gitattributes`, verified by
staging a file and confirming the warning is gone.

**Interview angle.** *"How do you make sure a 'we should fix this later' doesn't just evaporate?"*
Write it down somewhere structurally checked, not just said — this project's answer is
`PROGRESS.md`'s Known Deviations table, and M7 exists partly to audit that table for exactly this
gap.

#### D18 — Proving the quality gate against real Tesseract, not just a synthetic confidence dict

**What.** Sprint-1's own Definition of Done says *"quality gate triggers on a deliberately bad
photo."* Before M7, that was only proven two ways: `test_quality.py` (a pure function fed a
synthetic confidence dict — no OCR involved) and a manual dependency-override script used to
verify the frontend renders `RetakePrompt` correctly. Neither ran a real bad photo through real
Tesseract. `test_pipeline_e2e.py` now has a fixture built to defeat OCR on purpose — tiny
low-contrast text, then a heavy Gaussian blur — asserting the real pipeline lands on
`LOW_QUALITY`.

**Why it matters.** This is the same gap-between-"looks-done"-and-"is-done" pattern as D2 and
D12, at the level of an entire sprint's acceptance criteria rather than one function. A DoD
checklist item can be marked complete because *a* test exists near it, without that test actually
exercising the real path the checklist item describes.

**Interview angle.** *"You have a passing unit test for this behavior — why wasn't that enough?"*
A unit test proves the logic is correct given its inputs; it doesn't prove the real upstream
system (Tesseract, in this case) actually produces those inputs under the condition you claim to
handle. Both tests earn their keep for different reasons: the synthetic one is fast and covers
edge cases (word_count exactly at the boundary, etc.) that are hard to reliably reproduce with a
real image; the real one is the only proof the DoD claim is actually true.

### Review questions

1. **Read the code.** The bad-photo fixture in `test_pipeline_e2e.py` uses `fill=(232, 232, 232)`
   (very light gray, not pure white) and `GaussianBlur(radius=10)` together, rather than either
   alone. Why is the *combination* important — what could go wrong with only one of the two?
2. **Design.** `.gitattributes` marks `*.svg` as `-text` (no line-ending normalization at all,
   unlike `*.png`/`*.jpg` marked `binary`). SVG is actually a text format (XML). Why the different
   treatment, and what would break if SVGs were left under the default `* text=auto eol=lf` rule?
3. **Practice.** `PROGRESS.md`'s Sprint-1 review splits "not done" into three different reasons:
   *by design* (no deployment), *blocked on the owner* (golden letters, phone test), and *just not
   run yet*. Why does collapsing these into one "incomplete" bucket make the tracker less useful,
   not just less detailed?

### Teach-back

> **"Two things were technically 'known' for weeks and fixed by nobody — until we went looking on purpose."**
Explain the difference between a problem being *mentioned* and a problem being *tracked*, using
the `.gitattributes` fix (mentioned twice, fixed never — until a deliberate audit) as the example.

---

## M8 — Classification (first real LLM integration) *(done)*

### Decisions log

#### D19 — Response parsing is one shared, pure function across all three providers

**What.** `classify_document` on `OpenAIService`, `AzureOpenAIService`, and the new `GeminiService`
all call the same free function, `parse_classification_response(raw_text)` — none of them contain
their own JSON-parsing or fallback logic. Each adapter's job is only: build the prompt, call its
SDK, hand the raw text to the shared parser.

**Why.** This is the OCR-normalization pattern (D8) applied to LLM output: the interesting,
bug-prone logic (parsing, code-fence stripping, confidence clamping, the `other` fallback) lives
in exactly one place, unit-tested with 10 cases and zero network calls. Without this split, three
adapters would each need their own parsing tests, and a fix to one would not automatically fix
the others — the exact kind of drift D3's "one tool, one config" reasoning warns against.

**Interview angle.** *"You have three LLM providers. How do you keep their error handling
consistent?"* Don't let each adapter own its own parsing — push everything provider-agnostic
into a shared function the adapters merely call. The adapter's only job is the wire protocol.

#### D20 — Classification is best-effort: it can fail without failing the job

**What.** `JobService` calls the classifier only after the quality gate passes, and wraps the
call in a broad `except Exception` that logs a warning and leaves `doc_type: null` — the job
still reports `DONE`. A missing `GEMINI_API_KEY` (expected right now — no key has been obtained
yet), a network error, or a provider outage all look the same to the user: no badge on the
result, not a failure screen.

**Why.** OCR succeeding is the job's actual contract; classification is an enhancement layered on
top of it. Coupling the two would mean a temporarily-down LLM provider breaks uploads entirely,
which is a much worse failure mode than "the letter type badge didn't show up this time." This
is the same reasoning as D12 (OCR total-failure vs one-bad-page) inverted: there, isolating
*too* broadly hid a real failure; here, isolating classification *at all* is correct because it
is genuinely optional to the job's success.

**What was rejected.** Blocking job completion on classification succeeding (i.e., a job stays
`PROCESSING` until classification also finishes, or fails if it doesn't). Rejected because it
would make the entire upload flow depend on an external LLM being reachable and paid-for/free-
tier-available at every moment — a fragility with no upside, since M8 has no feature yet that
*requires* a doc_type to function (extraction's dependency on it is M9+).

**Interview angle.** *"When should a dependent feature's failure sink the whole request, versus
degrade gracefully?"* Ask whether the feature is on the critical path of what the user actually
asked for. Here, "read my letter" is the contract; "tell me what kind of letter it is" is an
enhancement — so its failure mode is a null field, not a 500.

#### D21 — `GEMINI_API_KEY` is a real, currently-unmet dependency — tracked, not hidden

**What.** No Gemini key has been obtained yet. Classification will degrade to `null` on every
real job until the owner adds one. This is recorded plainly in `PROGRESS.md`'s Known Deviations
table rather than glossed over.

**Why it matters enough to log.** Every previous "can't verify locally" gap in this project (no
Tesseract, no Docker, no `make`) got the same treatment: named specifically, not folded into a
vague "should work." A milestone that *looks* complete because the code compiles and unit tests
pass, while its one real integration point has never actually been exercised end-to-end, is
worth being honest about — especially on a project whose stated differentiator is honest
failure analysis over polished claims.

### Review questions

1. **Read the code.** `_classify` in `job_service.py` calls `get_ai_service()` *inside* the
   closure, not once outside it when `get_job_service()` is constructed. Why does that placement
   matter for what happens when the app boots without a `GEMINI_API_KEY` set?
2. **Design.** `JobService` depends on `ClassifierRunner = Callable[[str], ClassificationResult]`,
   not on `AIService` directly. What would `JobService`'s tests look like if it depended on the
   full `AIService` interface instead — what would every test have to additionally satisfy that
   they don't today?
3. **Practice.** `classify_document`'s prompt includes hand-written example letters (M8) while
   `eval/golden/` (M6) refuses to contain any fabricated ones. Both are "example German letters
   living in the repo" — what's the actual difference that makes one fine and the other a
   principle violation?

### Teach-back

> **"The AI feature can go down without the product going down."**
Explain why the job's success is defined by OCR succeeding, not by classification succeeding —
and why that specific line (not some other line) is where the failure isolation boundary sits.

---

## M9 — Extraction schemas (the frozen contract) *(done)*

### Decisions log

#### D22 — One common schema across all 8 letter types, not the plan's literal "top-4 + generic"

**What.** The execution plan's Day-9 text says "Pydantic schemas for top-4 types + generic" —
up to 5 distinct shapes. Built one instead: `LetterExtraction`, used identically for every
letter type, with `doc_type` deliberately excluded (it already lives on `JobResult` from M8's
classification, not duplicated here).

**Why.** `CLAUDE.md` §1 already defines a single field list — sender, dates, deadlines, amounts,
required actions, legal references — as the extraction target for *every* letter type. Building
4 bespoke schemas now would mean guessing which fields each type needs differently, with zero
golden letters to check the guess against. This is the same discipline as M6's refusal to
fabricate golden letters and M9's own "eval vs labeled set" deferral, applied to schema design
instead of test data: don't manufacture structure from imagination when real data could inform
it later. If real letters eventually show `bussgeld` genuinely needs a field `krankenkasse`
never has, that's a new ADR superseding this one — evidence-based, not guessed.

**Interview angle.** *"The spec said 4 schemas. Why did you build 1?"* Following a spec literally
when the spec's own higher-level document (`CLAUDE.md` §1) already implies something simpler is
not deference, it's carrying forward an inconsistency. State the conflict, pick the option
backed by more evidence (here: an explicit product-level field list vs. an arbitrary "top-4"
split with no criteria given for which 4), and write down why.

#### D23 — `source_span` embeds `BBox`es directly; never an index into the OCR document

**What.** `SourceSpan` is `{page: int, bboxes: list[BBox]}` — the actual frozen M3 bounding boxes
copied in, not indices into `OcrDocument.words` that the reader would have to resolve later.

**Why.** An index-based design would make every `ExtractedField` meaningless without also having
the exact `OcrDocument` it was computed against in hand — two objects that must always travel
together, with no way to enforce that pairing at the type level. Embedding the geometry directly
makes `ExtractedField` self-contained: the M18 overlay can render a highlight from the field
alone. This is the same reasoning that shaped `BBox` itself at M3 (ADR-0002) — resolve
coordinates to something the consumer can use standalone, not something requiring a second
lookup elsewhere.

**Interview angle.** *"Why duplicate the bounding box data instead of referencing it?"* Because
the two objects (`ExtractedField`, `OcrDocument`) would otherwise need to be threaded through
the same call chain forever to stay meaningful together — a form of the same coupling problem
dependency injection solves for services, applied to data instead of behavior.

#### D24 — Adopted Python 3.12+ native generics after checking they'd actually work

**What.** `ExtractedField[T]` uses PEP 695 syntax (`class ExtractedField[T](BaseModel)`), not the
classic `TypeVar` + `Generic[T]` pattern. Before committing to it, verified it against the
actually-installed Pydantic (2.13.4) rather than assuming — and, finding the project's pinned
floor (`pydantic>=2.9`) predates that support landing (~2.11), raised the floor to `>=2.11` so a
fresh `pip install` anywhere can't land on a version where this silently breaks.

**Why it matters.** This is the same instinct as M4's deskew prototype (D9): don't trust that a
plausible-looking feature works — check it against the real, installed version before writing
five files that depend on it. The gap here wasn't a bug, just an unverified assumption (a
version *range* includes versions that were never actually tested) that would have surfaced
later, in someone else's environment, as a confusing import-time error.

### Review questions

1. **Read the code.** `_field`'s `coerce` parameter returns `T | None`, and `_field` unconditionally
   sets confidence to `0.0` whenever the coerced value is `None` — even if the LLM reported a high
   confidence for that field. Why is overriding the LLM's own confidence number correct here?
2. **Design.** `LetterExtraction` has no `doc_type` field, even though a "type of letter" feels
   like exactly the kind of thing extraction would report. Why does it live on `JobResult`
   (M8) instead — and what would break if it were duplicated in both places?
3. **Practice.** `parse_letter_extraction` never raises, converting every failure mode into a
   null field. Contrast this with `document_pipeline.build_document`, which *does* raise
   (`DocumentOcrError`) when every OCR page fails (M5, D12). Why is total-failure-should-raise
   correct for OCR but total-failure-should-degrade correct for extraction parsing?

### Teach-back

> **"We built one schema instead of the four the plan asked for — because we had zero data to tell us the four should differ."**
Explain the difference between following a written plan and understanding what the plan was
trying to achieve, using this decision as the example.

---

## M10 — Extraction v1: live, with provenance *(done)*

### Decisions log

#### D25 — Source-span linking is its own pure module, not folded into the AI adapters

**What.** `link_source_spans(extraction, document)` lives in `services/source_span_linking.py`,
called by `JobService` *after* the AI adapter returns — the adapters (M9) never see an
`OcrDocument`, only flattened text. Matching splits further into candidate generators (what
surface forms could this value take in German?) and `find_source_span` (one simple word-window
search), each independently unit-tested with zero network and zero Tesseract calls.

**Why.** An LLM extracting "01.03.2026" as a `date` object has no reliable way to also report
*which pixels* that came from — it never saw pixels, only OCR's flattened text. Provenance has
to be computed after the fact, by a component that holds both the extracted value and the real
`OcrDocument` simultaneously. Keeping this pure and separate is the same discipline as OCR
normalization (D8) and classification/extraction parsing (D19, M9): the riskiest logic in the
codebase — matching, in this case — gets to be the most exhaustively tested, because nothing
about it depends on a live service.

**Interview angle.** *"Why not have the LLM return bounding boxes directly?"* Because it never
had access to word coordinates — asking it to would mean either feeding it raw OCR geometry
(expensive, unreliable) or trusting a fabricated answer. Compute provenance from what you
actually know, downstream of the model, not by asking the model to guess at data it never saw.

#### D26 — An unlinkable value gets its confidence *capped*, never zeroed and never left alone

**What.** When `find_source_span` can't match a field's value to any OCR word window, the field
keeps its value (it may still be correct) but its confidence is capped at `0.4` — never raised
above what the model originally reported, never dropped to `0.0` either.

**Why the cap, not zero.** Zeroing would claim "this is definitely wrong," which isn't true — the
model may have paraphrased or the letter may state it in a form the candidate generators don't
yet cover. Zero overclaims certainty in the other direction.

**Why the cap, not silence (leaving confidence untouched).** This is the actual design tension:
leaving a 0.9-confidence unlinked value at 0.9 would make an *ungrounded* claim look exactly as
trustworthy as a *verified* one, in a product whose entire differentiator is "click a field, see
it highlighted in your real letter." `CLAUDE.md` §5.2 already establishes the pattern for
deterministic validators — failures downgrade confidence and flag, they never silently pass —
and this extends that same rule to a new failure mode: "we could not verify this," not just
"this looks internally inconsistent."

**Interview angle.** *"Why 0.4 specifically, why not some other number?"* Honestly: a placeholder,
labeled as one, pending real-data tuning once golden letters exist (M13's decision point) — the
same posture as the OCR quality thresholds (M6). What matters for the interview answer isn't the
number, it's the *shape* of the rule: capped below whatever "trustworthy" means elsewhere in the
system, computed once, and never silently skipped.

#### D27 — List fields link to their first item only — a documented simplification, not silently dropped

**What.** `legal_references` and `required_actions` are `list[str]`, but `SourceSpan` is one
object per field, not one per list item. `_link_list` matches only `field.value[0]` and leaves
the rest of the list un-linked (the field's *value* still contains every item — only the *span*
covers the first).

**Why.** The alternative — a `SourceSpan` per list item — would mean changing `ExtractedField`'s
shape mid-freeze (ADR-0004 froze this schema at M9), for a case (multi-item lists on a single
letter) that has zero golden-letter evidence yet to justify the added complexity. Rather than
silently picking one behavior and letting a future reader guess why, it's named directly in the
code and here: a known, deliberate boundary, not an oversight.

**Interview angle.** *"Your list-field linking looks incomplete — first item only?"* Yes, on
purpose: it's the honest scope line between "ship the common case now" and "redesign a frozen
schema on a guess." Naming the limitation explicitly is the difference between technical debt and
technical debt no one on the team knows exists.

### Review questions

1. **Read the code.** `_link_scalar`'s `candidates_fn` parameter is `Callable[[T], list[str]]` —
   generic over the field's value type. Why does `sender` pass `lambda v: [v]` instead of a named
   function like `date_candidates`, and what would break (or not) if `str` fields also needed
   multiple candidate spellings?
2. **Design.** `find_source_span` tries window sizes from 1 up to 6 words, in ascending order, for
   every page before moving to the next. Construct a scenario (a real one, not contrived) where
   this ordering could return a *wrong* match instead of the intended one — and say whether that's
   actually a realistic risk given how candidates are generated today.
3. **Practice.** `UNVERIFIED_CONFIDENCE_CAP` is a module-level constant, not a `Settings` field
   like `min_mean_confidence`/`min_word_count` (M6). Why might that be the wrong call, and what
   would you check before deciding whether to promote it to a configurable setting?

### Teach-back

> **"An extracted value we can't verify keeps its answer, but loses its authority."**
Explain the difference between "wrong" (confidence 0), "right but unproven" (confidence capped),
and "verified" (confidence as reported, span attached) — and why collapsing any two of these
three states into one would break the trust story the source-highlight overlay is being built to tell.

### Post-merge fix: three CI failures misdiagnosed as digit-OCR uncertainty — the real bug was the test harness

**What happened.** `2571e9d` (M10's commit) failed CI. Two follow-up fixes targeted plausible
OCR-content problems (comma/currency candidate formatting, then OCR token-splitting whitespace);
a third made the test's assertions deliberately tolerant of imperfect digit recognition. All
three were reasoned from real, legitimate concerns — but all three were wrong, because none of
them was the actual failure.

The real error, once the log was actually read: `KeyError: 'status'` on a **404** from the `GET`
that immediately followed a **201** `POST` in the same test. `app.dependency_overrides[get_job_service]
= _real_ocr_service_with_fake_extractor` assigned the *factory function* as the override, not a
constructed instance. FastAPI calls an override fresh on every dependency resolution — so the
`POST` created a job in one `InMemoryJobRepository()`, and the following `GET` resolved a
brand-new, empty one. The job was never "hard to find" in real OCR output; it was **never in the
same repository as the request that looked for it.** Every other test in this file and in
`test_jobs.py` already gets this right (construct once, close over the instance in a lambda) —
this one test skipped that step.

**Why it matters more than the bug.** Three fix attempts were all aimed at the newest, most
complex, most "interesting" code in the change (the OCR-matching logic M10 actually introduced)
— because that's where a bug felt likely to be. The actual fault was in the oldest, simplest
pattern in the file, one line, copy-pasted incorrectly from code that has worked since M6. **The
instinct to suspect the complicated new thing before checking the simple scaffolding around it
is exactly backwards, and it cost three CI cycles.** The fix was available from the very first
failure — `KeyError: 'status'` on a 404 has nothing to do with digit recognition — but blind
guessing without reading the actual error meant three plausible-sounding wrong theories got
tested before the real one was even considered.

**What actually stopped the guessing.** Not a fourth theory — reading the real pytest output.
GitHub's Checks/annotations API exposes no structured per-test failure message without
repo-admin log access (confirmed twice this session), so the only paths were: install Tesseract
locally (blocked here — chocolatey needs elevation this shell doesn't have) or ask the owner to
copy the log from the browser. The second one, which should have been reached for immediately
after the *first* failed guess, not the third.

**Interview angle.** *"You spent three iterations on the wrong fix. What would you do differently
starting over?"* Read the actual error before forming a second hypothesis, let alone a third.
A blind fix is a bet; the payout for actually looking at the failure is almost always cheaper
than the cost of another guess-and-CI-cycle. And: when a new test fails, check the test's own
plumbing (fixtures, overrides, state sharing) before assuming the bug lives in the feature code
the test was written to exercise — simple scaffolding mistakes are more common, and cheaper to
rule out, than a fault in genuinely novel logic.

**What was reverted vs. kept.** The tokenization-whitespace normalization fix (`_normalize`
stripping all whitespace, not just outer) is a real, independently-good improvement — kept, and
still covered by its own unit tests. The relaxed e2e assertions (sender must link; only one of
three digit fields must) are also kept: digit-level OCR fidelity on a synthetic bitmap render is
still a genuinely untested variable, now that the test can actually reach that code path for the
first time — honesty about that uncertainty is warranted regardless of what caused this
particular failure.

---

## M11 — Deterministic validation: impossible values, caught and flagged *(done)*

### A note on process for M11 onward

The owner explicitly chose "full speed, review later" (2026-08-13): milestones M11–M30 are built
back to back, with a Plan Gate and Milestone Review still written for each (this section is that
record), but without pausing for approval or waiting on engagement between them. This is a
deliberate, owner-made trade-off against `CLAUDE.md` §6's default protocol, not a silent skip —
logged in `PROGRESS.md`'s Known Deviations table so it stays visible. M1–M10's review questions
remain open and unanswered; M11's are added to the same pile, to be worked through in one batch
later rather than blocking forward progress now.

### Plan Gate

**What.** `services/validators.py`: pure functions checking `deadline >= letter_date`,
`amount >= 0`, and each `legal_references` entry against a curated § whitelist. A failure appends
a code to a new `ExtractedField.validation_issues: list[str]` field and caps confidence — never
rewrites the value. Wired into `JobService` right after M10's `link_source_spans`. Frontend gets a
`⚠ flagged` badge in `ExtractionSummary`.

**Files touched.** `backend/app/schemas/extraction.py` (additive field), new
`backend/app/services/validators.py`, `backend/app/services/job_service.py` (one new call),
`backend/app/tests/test_validators.py` (new), `backend/app/tests/test_jobs.py` (2 new tests),
`frontend/src/types/job.ts`, `frontend/src/components/ExtractionSummary.tsx`,
`docs/adr/0005-validation-issues-additive-field-on-extractedfield.md`.

**The trade-off.** Extending `ExtractedField` — frozen by ADR-0004 — versus a separate
`ValidationResult` object correlated by field name. Chose the extension: keeping a flag on the
field it describes avoids forcing the frontend to cross-reference two structures for one badge,
and the freeze exists to protect *golden fixtures* from schema churn, not to block a genuinely
additive, backward-compatible field before any fixtures exist. Full reasoning in ADR-0005.

### Decisions log

#### D28 — `validation_issues` is a `list[str]` of codes, not a `bool`

**What.** A failed check appends a short machine-readable string (`"negative_amount"`) to a list
on the field, rather than flipping a single `is_valid` boolean.

**Why.** A boolean discards *why* — information the frontend already needs (the `⚠ flagged`
tooltip) and that a future eval scorecard (M12) will need to break failures down by category
instead of one undifferentiated bucket. A list also survives a field failing more than one check
at once without redesign, which a single boolean can't represent at all.

**Interview angle.** *"Why not just a string, if today only one issue ever fires per field?"* Because
designing for today's actual constraint ("exactly one check per field is currently possible") into
the data shape itself is exactly the kind of premature narrowing that breaks the next time someone
adds a fourth rule — a list costs nothing extra today and doesn't need a migration later.

#### D29 — Two independent confidence ceilings that compose via `min()`, not one shared cap

**What.** Source-span linking (M10) caps unverifiable values at `0.4`. Validation (M11) caps
semantically-impossible values at `0.2`, applied as a *second*, independent `min()` on top of
whatever linking already produced — never as a replacement.

**Why.** These are different severities of "don't fully trust this": "could not confirm this
appears in the letter" is weaker evidence of an actual error than "this value contradicts another
value from the same letter." Collapsing them into one shared cap would make an internally
consistent-but-unlinked value (e.g., a real amount the candidate generators just don't have a
surface form for) look exactly as suspect as one that's flatly self-contradictory — the same
information-loss mistake D26 already rejected once, now showing up at the boundary between two
mechanisms instead of within one.

**Interview angle.** *"Why not have validation run first, then linking?"* Order was chosen
deliberately: linking answers "is this grounded in the source text," validation answers "is this
internally plausible" — grounding is checked before plausibility because a value that isn't even
in the letter shouldn't get credit for looking numerically reasonable. In practice the `min()`
composition makes the order not actually change the final confidence for any single-failure case,
but it does change *which* flag a reader sees attached first if both were to run and inspect
intermediate state — worth being able to explain even though it isn't currently observable from
the API response.

#### D30 — The § whitelist flags the whole `legal_references` field, not the one bad entry

**What.** If any single reference in the list fails the whitelist check, `unrecognized_legal_reference`
is appended once, to the field — not per-item, and the rest of the (possibly-valid) references in
the same list aren't distinguished from the bad one.

**Why.** Same simplification `SourceSpan` already made for this exact field in D27 (M10): the
schema wraps one list value per field, not one wrapper per list item. Adding per-item validation
state would mean either a schema shape change mid-freeze or a second, parallel data structure
side-by-side with the list — for a case with zero golden-letter evidence yet showing how often
multi-reference letters with mixed valid/invalid citations actually occur.

**Interview angle.** *"Isn't flagging the whole list overly broad if only one of three references
is bad?"* Yes, named directly as a known boundary rather than hidden — the same honest-scope-line
argument D27 already made. If real data shows multi-reference letters are common and the coarse
flag is actively misleading, that's a concrete, evidence-based reason to revisit the schema; guessing
now, with no letters to check the guess against, isn't.

### Review questions

1. **Read the code.** `_validate_deadline` and `_validate_amount` take concrete types
   (`ExtractedField[date]`, `ExtractedField[Decimal]`) while `_flag` is generic (`_flag[T]`). Why
   does the generic version exist at all if only two concrete call sites use it today, and what
   would you lose by inlining the confidence-cap logic directly into each validator instead?
2. **Design.** `VALIDATION_FAILURE_CONFIDENCE_CAP` (0.2) is lower than
   `UNVERIFIED_CONFIDENCE_CAP` (0.4) from M10. Construct a realistic letter scenario where a value
   fails *both* checks at once, and trace through exactly what confidence the API response would
   show and why — then say whether that final number still communicates something meaningfully
   different from a value that only failed one of the two checks.
3. **Practice.** `is_recognized_legal_reference` is exported as a public function from
   `validators.py`, while `_validate_deadline`, `_validate_amount`, and `_validate_legal_references`
   are all prefixed private. What's the actual reason one function in this module needed to be
   part of the public interface and the other three didn't — check the test file if the answer
   isn't obvious from the module alone?

### Teach-back

> **"An impossible value doesn't get corrected or hidden — it gets a lower trust score and an honest reason why."**
Explain the difference between what M10's source-span cap means ("I can't prove this is in the
letter") and what M11's validation cap means ("this contradicts another value from the same
letter"), and why a system that silently "fixed" a deadline that falls before its own letter date
would be a worse product than one that just shows the contradiction and lets the user judge it —
even though "fixing" it would look more polished in a demo.

---

## M12 — Eval harness: scoring taxonomy, run_eval.py, CI wiring *(partial — blocked on real letters)*

### Plan Gate

**What.** `eval/scoring.py`: a pure, zero-dependency 5-outcome comparator (`correct` /
`correct_null` / `missed` / `wrong` / `hallucinated`) between a label and an extraction, plus
aggregation and a markdown scorecard generator. `eval/run_eval.py`: the CLI that actually runs the
real pipeline against every `eval/golden/manifest.json` entry and writes `eval/scorecard.md`. Wired
into CI as extra steps in the existing `backend` job.

**Files touched.** New `eval/scoring.py`, `eval/run_eval.py`, `eval/pyproject.toml`,
`eval/tests/test_scoring.py`, `eval/tests/test_run_eval_e2e.py`, `eval/tests/conftest.py`;
`.github/workflows/ci.yml` (6 new steps); `docs/adr/0006-eval-scoring-taxonomy-five-outcomes-not-a-boolean.md`.

**The trade-off.** Building the full harness now, against 0 golden letters, versus waiting for the
owner to collect letters first. Chose to build now: the scoring taxonomy, the pipeline wiring, and
the CI gate are all real engineering work independent of any specific letter, and proving the
harness itself is correct (via a real-OCR CI-gated test with fake classifier/extractor injection,
same pattern as M10's `test_extraction_e2e.py`) doesn't require real data — only the actual
baseline numbers do, and those stay honestly blocked. Full reasoning on the taxonomy itself in
ADR-0006.

**What's genuinely blocked, not skipped.** M12's own acceptance criterion — "I can see published
per-field accuracy on real letters" — cannot be met without real letters, which cannot be
fabricated (M6's D15, reaffirmed here). `scorecard.md` says this explicitly rather than showing a
fake or empty-looking table.

### Decisions log

#### D31 — Five outcomes, not a boolean, and `HALLUCINATED` is called out as the important one

**What.** `score_field` returns one of `CORRECT`, `CORRECT_NULL`, `MISSED`, `WRONG`,
`HALLUCINATED` — never a plain `bool`. The generated scorecard markdown explicitly states that a
non-zero `HALLUCINATED` count matters more than the headline accuracy percentage.

**Why.** A single accuracy number can't distinguish "the model honestly said null on a hard case"
from "the model invented a plausible-looking value the letter never had" — and those are not
equally bad. Collapsing them into one `wrong` bucket would hide the exact failure mode
null-not-guess (`CLAUDE.md` §5.1) exists to prevent, making the scorecard measure something other
than what actually matters for this product.

**Interview angle.** *"Why five categories and not, say, three?"* Each one answers a different
question a reviewer would actually ask: `CORRECT`/`CORRECT_NULL` answer "did it work," `MISSED`
answers "is the model too conservative," `WRONG` answers "is the model confidently incorrect," and
`HALLUCINATED` answers "does the model invent things" — the single question this whole project is
built to answer honestly. Fewer categories would merge two of those questions into one answer.

#### D32 — `run_eval.py` injects the classifier/extractor, reusing `JobService`'s own seam

**What.** `score_one_document` takes `classifier: ClassifierRunner | None` and
`extractor: ExtractorRunner | None` as parameters — the exact type aliases already defined in
`app.services.job_service` — rather than calling `get_ai_service()` inline.

**Why.** The same reason `JobService` itself is built this way: it makes the OCR + scoring wiring
testable against a real rendered PDF, through real Tesseract, without a live (and non-deterministic,
rate-limited, non-free-in-CI-minutes) LLM call. `eval/tests/test_run_eval_e2e.py` proves this
directly — the fake extractor deliberately gets one field wrong, so the test proves `score_document`
ran on real pipeline output rather than a stub that always reports success.

**Interview angle.** *"Isn't this over-engineering for a one-off eval script?"* No — reusing an
existing, already-proven seam is the opposite of over-engineering; the alternative (calling
`get_ai_service()` directly inside `run_eval.py`) would have made the harness itself untestable
without either a real API key or a second, parallel mocking strategy the codebase doesn't otherwise
need.

#### D33 — The scorecard is explicit about 0 documents rather than rendering an empty or fabricated table

**What.** `generate_scorecard_markdown` special-cases `document_count == 0`: instead of an empty
table (technically true, easy to misread as "0% everywhere" or "nothing to report") it writes a
plain-language paragraph naming the exact reason and pointing at `eval/golden/README.md`.

**Why.** An empty or all-zero-looking table in a portfolio project reads ambiguously — did nothing
run, or did everything fail? Given this project's whole differentiator is honesty about what it
does and doesn't know, the harness's own output about *itself* needed to hold to the same standard.

**Interview angle.** *"Why not just skip generating a scorecard at 0 documents?"* Because "the
harness runs and produces a correct, honest result" is itself worth proving in CI on every push,
not just once real letters exist — a skip would mean a broken harness could sit undetected until
the day someone actually needs it.

### Review questions

1. **Read the code.** `_norm_list` in `scoring.py` treats an empty list and `None` as the same
   "nothing here" state. Trace through what `score_field("legal_references", [], ["§ 152 AO"])`
   returns and why — then explain why this specific case (label says empty, extraction lists
   something) is scored as `HALLUCINATED` rather than `WRONG`.
2. **Design.** `field_accuracy` counts `CORRECT_NULL` as "correct." Construct a golden set where a
   field is null on every single letter (e.g., `amount` on a `krankenkasse` letter type that never
   mentions money) — what would that field's accuracy read as, and is that number actually useful,
   or does it need a different presentation (e.g., excluding fields with very few non-null labels)?
3. **Practice.** `eval/pyproject.toml` sets `mypy_path = "../backend"` so `run_eval.py`'s
   `app.*` imports type-check, while `scoring.py` has zero such imports at all. What would you lose,
   architecturally, if `scoring.py` also imported directly from `app.schemas.extraction` instead of
   operating on plain dicts?

### Teach-back

> **"The most important number in this scorecard isn't the accuracy percentage — it's the hallucination count."**
Explain, in a way a non-technical hiring manager would follow, why a system that's 85% accurate but
never hallucinates is a better product than one that's 92% accurate but occasionally invents a
deadline — and why a scorecard that only reports the single accuracy number would hide that
difference entirely.

---

## M14 — Confidence tiers *(partial — golden set + retro are the owner's task)*

### Plan Gate

**What.** `frontend/src/lib/confidence.ts`: a pure `confidenceTier(confidence: number)` function
bucketing the raw `[0,1]` value into `"high" | "medium" | "low"`, wired into `ExtractionSummary` as
color-coded confidence text.

**Files touched.** New `frontend/src/lib/confidence.ts`; `frontend/src/components/ExtractionSummary.tsx`.

**The trade-off.** Computing the tier on the frontend from the confidence value already in the API
response, versus adding a `confidence_tier` field to the backend's `ExtractedField` schema. Chose
the frontend: tiering is purely a presentation decision (where to draw the line on a display), not
new information the pipeline computes — adding a backend field would mean extending the ADR-0004/
ADR-0005 contract for something fully derivable from data already being sent, which is the same
minimal-surface argument this project has applied at every schema decision so far.

**No ADR.** Per `docs/adr/README.md`'s own bar ("things that constrain later milestones," not
routine choices), this doesn't qualify — the thresholds are a small, easily-revised display
constant, not something that locks in a schema, a provider, or a fixture format.

### Decisions log

#### D34 — Tier thresholds are aligned to the pipeline's own existing confidence caps, not independently chosen

**What.** The medium/low boundary is 0.4 — not a round number picked for its own sake, but exactly
`source_span_linking.UNVERIFIED_CONFIDENCE_CAP` (M10). The high/medium boundary (0.8) is the one
genuinely new constant this milestone introduces.

**Why.** An unverified value is *by construction* capped at 0.4, so if the tier boundary had been
placed anywhere else, "unverified" and "low confidence" would disagree with each other on some
subset of values — a value could show as "medium confidence" in the tier badge while its own
tooltip says "could not be matched back to the letter text," which reads as contradictory. Reusing
the existing cap as the boundary keeps the two signals (verified/unverified, tier color) coherent
with each other instead of being two independently-tuned opinions that can drift apart.

**Interview angle.** *"Why not just make the tier thresholds configurable, like the OCR quality
gate's settings?"* `min_mean_confidence`/`min_word_count` (M6) gate a *decision* (retake or not) with
real product consequences if tuned wrong; confidence tiers are read-only presentation sugar with no
downstream branching — over-engineering a settings surface for a value nothing else depends on
would add configuration surface area for a problem that doesn't exist yet.

#### D35 — The tier recolors the confidence percentage; it doesn't replace the verified/unverified badge

**What.** `ExtractionSummary` keeps the raw percentage number, the ✓/unverified label, and the
⚠ flagged badge exactly as M10/M11 built them — the tier only changes what color the confidence
text renders in.

**Why.** Collapsing everything into a single "High/Medium/Low" word would lose the precise
percentage (some users will want to know it's specifically 42%, not just "medium") and would blur
together three distinct questions this UI already answers separately: is it grounded in the source
text (verified), is it internally consistent (flagged), and how confident should you be overall
(tier). Replacing three signals with one summary judgment is exactly the kind of information loss
D28 (M12's scoring taxonomy) already rejected once, in a different part of the same product.

**Interview angle.** *"Doesn't showing four different confidence signals on one field overwhelm a
non-technical user?"* Fair challenge — the honest answer is this is the developer-facing/portfolio
density of the signal today; the actual product decision about how much of this a real end user
should see at once (versus behind a "why?" affordance) is a UX call for M17's results-page pass, not
something to resolve by deleting information now.

### Review questions

1. **Read the code.** `confidenceTier` uses `>=` for both thresholds (`confidence >= 0.8`,
   `confidence >= 0.4`). Trace through what tier a field with confidence exactly `0.4` — precisely
   `UNVERIFIED_CONFIDENCE_CAP` — receives, and confirm that matches what you'd intuitively expect an
   "unverified" field to look like.
2. **Design.** If `VALIDATION_FAILURE_CONFIDENCE_CAP` (M11, currently 0.2) were ever changed to
   something above 0.4, what would happen to how a validation-flagged field displays, and would that
   still make sense next to the ⚠ flagged badge?
3. **Practice.** `confidence.ts` has no automated test — this project has no frontend test framework
   set up yet (`frontend/package.json` only runs lint/format/build in CI). What did verifying this
   milestone actually rely on instead, and what's the concrete risk of that gap the next time this
   file changes?

### Teach-back

> **"The tier color and the verified badge can point in different directions, and that's correct, not a bug."**
Explain a real scenario where a field is "medium confidence" (amber) but still shows "unverified,"
and a different scenario where a field could be "medium confidence" while showing verified — then
explain why forcing these two signals to always agree would actually make the UI less honest, not more.

---

### Post-merge fix: four real bugs surfaced by testing with a real Gemini key for the first time

**What happened.** M8–M11 were built and tested entirely against a missing `GEMINI_API_KEY` —
classification and extraction always took the "no key configured" branch of their own best-effort
error handling, so the actual live-API code paths had never once executed. The owner added a real
free-tier key and asked for M13/M14 to be tested live. The very first real upload came back with
`doc_type: null, extraction: null` — everything degraded exactly like a missing key, except the key
was now present. Getting to a genuinely working end-to-end run took four separate real bugs, found
and fixed in sequence:

**Bug 1 — `get_ai_service()`'s `@lru_cache` shared one client across independent event loops.**
`JobService._classify`/`_extract` each call `asyncio.run(...)` — creating and closing a fresh event
loop per call. The cached `AIService` (and its underlying `httpx.AsyncClient`) was constructed once
and reused across every call, system-wide. Its connections got bound to whichever loop was active
when they opened; the next `asyncio.run()` call created a new loop, and cleanup of a stale
connection from a now-closed loop raised `RuntimeError: Event loop is closed`. Fix: removed
`@lru_cache` from `get_ai_service()` (`factory.py`) — a fresh client per call costs one cheap object
allocation, not a network call, and scopes every client to the loop that will actually use it.

**Bug 2 — the configured Gemini model (`gemini-2.0-flash`) had been retired by Google.** A live 404
named the exact model as no longer available. Bumped to `gemini-2.5-flash` — which turned out to
also be retired for this (new) API key, a second live 404. Queried `client.models.list()` directly
against the real key and test-called several current candidates; landed on `gemini-3.5-flash`,
verified working. Pinned rather than tracking the `gemini-flash-latest` alias, so the next such
retirement is a deliberate version bump in a commit, not a silent behavior change from Google's side
mid-project.

**Bug 3 — `response_mime_type="application/json"` is not reliably honored.** Even after bugs 1–2
were fixed, extraction came back with every field null despite Gemini answering `200 OK`. The raw
response text showed why: a syntactically perfect JSON object with an unsolicited explanatory
sentence appended after it (a second live call instead wrapped the JSON with prose *before* it).
Plain `json.loads` rejects trailing (or leading) content as a hard error, so the null-not-guess
fallback fired for the wrong reason — treating a genuinely correct extraction as malformed. Fix: new
shared `app/services/ai/json_parsing.py` — finds the first `{`/`[` in the response and lets
`json.JSONDecoder.raw_decode` parse one value from there, ignoring whatever precedes or follows.
Both `extraction_parsing.py` and `classification_parsing.py` (previously each hand-rolling the same
code-fence-strip-then-`json.loads` logic) now share this one function.

**Bug 4 — a latent test-isolation gap, invisible until a real key existed.**
`test_pipeline_e2e.py` (M5) used the raw `TestClient(app)` with no dependency override, meaning it
exercised the real `get_job_service()` factory — which, since M8/M10, wires in real classification
and extraction whenever an `AI_PROVIDER`/key happen to be configured. With no key, those calls
failed in milliseconds via JobService's own best-effort handling, so this was invisible for the
project's entire life so far. With a real key, the same test started making real, slow (and
occasionally `503`-flaky) network calls to score something — OCR pipeline mechanics — that has
nothing to do with classification or extraction, and started timing out past its 30-second poll
window. Fix: this test now constructs its own `JobService` with the real OCR pipeline but
`classifier=None, extractor=None`, overridden via `app.dependency_overrides` — the same
"override, don't depend on ambient config" discipline `test_jobs.py` and `test_extraction_e2e.py`
already used, just never applied here because the gap had never been exercised.

**Why it matters more than any individual bug.** All four were invisible for the entire project
so far, for the same underlying reason: no test suite, however thorough, exercises a code path that
a missing API key short-circuits before it ever runs. 165 backend tests and 23 eval tests were all
green throughout — correctly, they were testing exactly what they claimed to test — but "the app
works" and "the app works with 0 of the 3 real external dependencies actually engaged" had quietly
become the same claim. The fix wasn't better tests; CI still can't run these live-API paths without
either paying or making CI flaky against a real quota. It was a first real end-to-end run, which no
amount of well-designed mocking substitutes for.

**Interview angle.** *"How would you have caught these earlier?"* Honestly, mocking discipline is
exactly what *prevented* catching them earlier — every unit and integration test correctly avoided
live network calls, which is right for CI, but it means "all tests green" was never evidence that
the real Gemini integration worked, only that the code around it was internally consistent. The
actual answer is a periodic, manually-triggered smoke test against the real provider (not run in
CI, not gating merges, just run deliberately before claiming a feature "works") — this session was,
in effect, the first one this project ever had.

**What was verified, not just fixed.** After all four fixes: a real upload of a synthetic German
letter through the actual running app produced real OCR text (92% confidence), real classification
(`finanzamt`, 100% confidence), and real extraction with every field populated and source-span-linked
against the real OCR output — including a genuine, correct catch by M11's validator: "Paragraph 152
AO" (the letter's actual wording) got flagged `unrecognized_legal_reference` because the curated
whitelist regex only recognizes the `§` symbol, not the spelled-out German word "Paragraph" — a real
gap in the whitelist, not a bug in the flagging logic, and exactly the kind of finding M13's
eventual real-data tuning pass exists to catch.

---

## M15 — Grounded explanation: readability, advice linter, disclaimer *(done)*

### Plan Gate

**What.** Retire the unused M1 `summarize` placeholder (0 real callers, 0 tests) in favor of a real
`explain_document` operation across all 3 providers, grounded in the letter text plus the
already-extracted fields. Two independent, non-negotiable safeguards against giving legal advice
(RDG risk): the prompt itself, and a deterministic `advice_linter.py` that checks the model's actual
output. `readability.py` computes word count + Flesch Reading Ease against the ≤200-word/B1 target.
Wired into `JobService` as a third independent best-effort step. Frontend gets a persistent
`Disclaimer` and an `ExplanationCard` that shows a visible warning, never hides the text, when either
check fails.

**Files touched.** `backend/app/schemas/ai.py` (removed `Summarization*`, added
`DocumentExplanation*`), `backend/app/schemas/explanation.py` (new), `backend/app/services/ai/base.py`,
all 3 providers, `backend/app/services/ai/prompts/explain.py` (new),
`backend/app/services/ai/explanation_parsing.py` (new), `backend/app/services/readability.py` (new),
`backend/app/services/advice_linter.py` (new), `backend/app/services/job_service.py`,
`frontend/src/components/Disclaimer.tsx` (new), `frontend/src/components/ExplanationCard.tsx` (new),
`frontend/src/app/result/[id]/page.tsx`, `docs/adr/0007-grounded-explanation-and-the-advice-linter.md`.

**The trade-off.** One safeguard (the prompt) versus two (prompt + linter). Chose two, deliberately
redundant: `response_mime_type="application/json"` was already proven, live, not to be reliably
honored by the actual model in use (this same session's bug 3) — direct evidence that trusting a
model's instructions to hold perfectly, unchecked, is not a safe assumption anywhere in this
codebase, and the least acceptable place to make that exception is the one feature with real legal
exposure. Full reasoning in ADR-0007.

### Decisions log

#### D36 — `summarize` deleted outright, not deprecated alongside `explain_document`

**What.** The M1 `SummarizationRequest`/`SummarizationResult`/`AIService.summarize` trio — zero real
callers, zero tests, ever — was removed entirely rather than left in place next to the new
`explain_document`.

**Why.** It wasn't actually usable for M15's need (grounding in extracted fields, not just a content
string), and keeping unused, misleading code around "in case something needs it later" is exactly
what ADR-0004 already rejected once for `DocumentExtractionResult`: two names for one concept,
forever, is worse than deleting speculative code nothing depends on.

**Interview angle.** *"Why not keep summarize as a separate, simpler operation for future use?"*
YAGNI — a method with genuinely zero callers across the entire codebase's life isn't validated design,
it's a guess that was never spent. If a real future need for plain summarization (not grounded
explanation) appears, it gets designed against that real need, the same way `explain_document` itself
was designed against M15's actual requirement instead of contorting the old placeholder to fit.

#### D37 — Readability and the advice linter run on the model's output, not inside the prompt's contract

**What.** `assess_readability` and `find_advice_phrases` are pure functions in `services/`, called by
`JobService` after `explain_document` returns — not something the AI adapter or the prompt computes
or self-reports.

**Why.** Same split M9/M10/M11 established for extraction: what the model *claims* (the raw
`DocumentExplanationResult.explanation` string) versus what can be independently *verified* about
that claim (word count, Flesch score, advice phrases) are kept as separate fields computed by
separate, independently-testable code — never folded into a single value the frontend has to trust
blindly. A model cannot be trusted to accurately self-report whether its own output violates a
constraint it was told to follow; that's exactly the case this whole codebase's validator pattern
exists to cover.

**Interview angle.** *"Why compute Flesch Reading Ease yourself instead of asking the model to
self-report a readability score?"* Because asking the model to grade its own homework has no
guarantee of correlating with the actual text it produced — a deterministic, well-defined formula
computed independently is falsifiable and reproducible; a self-reported number is neither.

#### D38 — A flagged explanation is still shown, in full, with the flag attached

**What.** When `advice_phrases_found` is non-empty, or the explanation exceeds 200 words, or its
Flesch score is below target, `ExplanationCard` still renders the complete, unmodified text — it adds
a visible warning below it, it does not truncate, rewrite, or hide the explanation.

**Why.** Truncating prose risks cutting it off mid-sentence and changing its meaning; "simplifying"
text algorithmically without a second LLM call isn't achievable deterministically, and a second LLM
call reintroduces the exact grounding risk being guarded against, while also spending real free-tier
quota (a genuinely scarce resource this session ran out of) on a problem a flag already communicates
honestly. This mirrors D14 (M6): withholding OCR text below a confidence threshold was the right call
there because the text was actively unreliable; here, the text is likely still an accurate
description that merely also contains a phrase worth a human's attention — a different situation,
correctly given a different (flag, don't hide) treatment.

**Interview angle.** *"Isn't shipping a flagged advice-like sentence to the user risky?"* The flag is
the safety mechanism, not a decoration — a visible, specific warning next to a phrase like "you
should pay now" is a materially different risk posture than the same phrase presented with no warning
at all. The alternative (silently blocking the whole explanation) would make a partially-good
explanation unavailable over one flagged sentence, which is a worse outcome for a user who still needs
to understand the rest of the letter.

### Review questions

1. **Read the code.** `job_service.py`'s explanation step falls back to `_empty_extraction()` when
   `result.extraction` is `None`. Trace through exactly when that happens — list the 2 distinct
   scenarios — and explain why an all-null `LetterExtraction` is still valid input to
   `build_explanation_user_message` rather than something that should skip explanation entirely.
2. **Design.** `MIN_FLESCH_READING_EASE = 60.0` is a module-level constant with no real-user
   validation yet (the docstring says so directly). What would you actually need to collect, from
   whom, before you could defend changing this number in a code review?
3. **Practice.** `advice_linter.py`'s docstring explicitly calls itself "a floor, not a guarantee."
   Name one advice-giving phrasing a determined model could produce that would slip past every
   pattern in `_ADVICE_PATTERNS` today, and say what (if anything) could catch it instead.

### Teach-back

> **"Two independent checks catch what one check, however well-designed, might miss."**
Explain why relying only on the explanation prompt's own no-advice instructions would have been
insufficient here — using this session's own evidence (a live Gemini call that didn't honor
`response_mime_type="application/json"`) to argue why "the instructions should work" is not the same
claim as "the instructions did work," and why a product with real legal exposure needs the second
claim, verified, not just the first, hoped.

---

## M16 — Action checklist + Amtsdeutsch glossary *(done)*

### Plan Gate

**What.** `checklist.ts`: a pure function deriving an urgency-flagged action checklist from the
already-extracted `required_actions` and `deadline` — zero new AI calls, zero schema changes.
`glossary.ts`: a curated set of real German bureaucratic terms with plain-English definitions;
`GlossaryText` makes every occurrence in rendered text tappable, showing its definition inline.

**Files touched.** New `frontend/src/lib/checklist.ts`, `frontend/src/lib/glossary.ts`,
`frontend/src/components/ActionChecklist.tsx`, `frontend/src/components/GlossaryText.tsx`;
`frontend/src/components/ExplanationCard.tsx` and `frontend/src/app/result/[id]/page.tsx` wired to use
both.

**The trade-off.** A backend-driven checklist (a new AI operation deriving per-action deadlines and
urgency) versus a pure frontend derivation from data already in `LetterExtraction`. Chose the
frontend derivation: the extraction schema has exactly one `deadline` per letter (ADR-0004, frozen),
so there is no per-action deadline data to derive from without a schema change nothing in this
milestone's actual requirement justifies yet; and "urgent" is inherently relative to *today*, which a
value computed once at processing time and stored would silently go stale the next time a user
revisits an old result page.

### Decisions log

#### D39 — Urgency is computed at render time, never stored on the job

**What.** `buildChecklist` runs in the browser, using `new Date()` at call time — it is not computed
once in `JobService` and persisted onto `JobResult`.

**Why.** "Urgent" means "within 14 days of right now." A value baked in at processing time would be
correct only on the day the job ran; reopening the same result a week later would show a stale,
increasingly wrong urgency flag with no way to know it had gone stale. Computing it at render time
means it's always accurate for whoever is looking at it, at no cost — the underlying data
(`required_actions`, `deadline`) doesn't change, only the "how soon is that" judgment does.

**Interview angle.** *"Isn't recomputing this on every render wasteful?"* No — it's a handful of
date-arithmetic operations on a handful of strings, not a network call or anything that benefits from
caching. The actual engineering principle here isn't performance, it's correctness: a value that is a
function of "now" should be computed when "now" is actually needed, not memoized somewhere it can
silently drift from reality.

#### D40 — The glossary is a static, curated frontend asset, not an AI-generated or backend-served one

**What.** `GLOSSARY` in `glossary.ts` is a hand-curated `Record<string, string>` shipped with the
frontend bundle — not fetched from an API, not generated by an LLM at request time.

**Why.** The definitions need to be correct and stable; asking an LLM to define a bureaucratic term
on demand reintroduces exactly the grounding/hallucination risk M15's whole design (ADR-0007) exists
to keep out of user-facing text, for content that doesn't need to be dynamic in the first place — a
term's definition doesn't depend on which letter it appeared in. A static asset is also free (no API
call, no added latency) and trivially cacheable by the browser.

**Interview angle.** *"58 terms is a lot smaller than the full space of Amtsdeutsch vocabulary — what
happens when a letter uses a term that isn't in the glossary?"* It's simply not tappable — the text
renders as plain, unstyled text, exactly like any other word. No fallback guess, no broken UI, no
false claim of coverage — the same "curated, not exhaustive, never silently wrong" posture as
`validators.py`'s § whitelist (M11) and `advice_linter.py`'s pattern list (M15).

### Review questions

1. **Read the code.** `GlossaryText`'s `TERM_PATTERN` regex is built once at module scope, not inside
   the component function. What would break, or just get slower, if it were rebuilt on every render
   instead — and why does `String.prototype.split` make a shared, stateful global-flag regex safe to
   reuse here, when `.exec()`/`.test()` in a loop would not be?
2. **Design.** `buildChecklist` gives every `required_actions` item the *same* deadline and urgency,
   because the schema only has one. Construct a real letter scenario (a genuine one, not contrived)
   where a letter plausibly has two required actions with two different real-world deadlines — what
   would actually need to change, starting from `ExtractedField`, to represent that honestly?
3. **Practice.** This milestone shipped with no new automated tests (the checklist and glossary logic
   are pure TypeScript functions, but this project still has no frontend test framework — a gap
   already named in M14's review questions). What's the concrete cost of that gap specifically for
   `buildChecklist`'s urgency-window boundary (exactly 14 days) — the kind of off-by-one a unit test
   would catch immediately but manual browser verification easily misses?

### Teach-back

> **"The glossary and the advice linter are the same idea applied to two different problems: a
> curated, honestly-incomplete list beats a dynamically-generated one whenever correctness matters
> more than coverage."**
Explain why BriefPilot chose to hand-write 58 term definitions instead of asking Gemini to define
unfamiliar words on the fly — and connect it to the exact same trade-off M11's § whitelist and M15's
advice-phrase list already made, so a reader can see this isn't three separate decisions, it's one
principle applied three times.

---

## M17 — One clear results page *(done — mostly a consolidation pass)*

### Plan Gate

**What.** By the time M17 came up, explanation (M15) and checklist (M16) already existed on the
results page — this milestone's real remaining work was a `SummaryCard` (sender/deadline/amount at a
glance, at the top of the page) and confirming the page actually holds together as "one clear results
page" on a real mobile viewport, not just at desktop width.

**Files touched.** New `frontend/src/components/SummaryCard.tsx`;
`frontend/src/app/result/[id]/page.tsx` (wired it in, renamed the now-stale "Extracted text" header to
"Your letter").

**The trade-off.** Building new UI to prove mobile-readiness versus trusting Tailwind's responsive
utility classes (already used throughout) to just work. Chose to actually measure it —
`document.documentElement.scrollWidth` vs. `clientWidth` at a real 375px viewport — rather than assume
responsive classes are sufficient just because they're present in the markup; a `grid-cols-3` that
forgot its `sm:` prefix would look identical in the source and broken on a phone.

### Decisions log

#### D41 — Most of M17 was recognizing what was already done, not building new things

**What.** Reviewing `PROGRESS.md`'s M17 requirements against the actual current state of the results
page showed 3 of 5 listed items (explanation, checklist, honest processing/error states) already
shipped in earlier milestones. Only the summary card and a mobile-width check were genuinely new.

**Why.** Worth naming explicitly: the milestone list in `PROGRESS.md` was written before M15/M16
existed, describing a results page that hadn't been built incrementally yet. Re-verifying already-built
pieces against a later milestone's acceptance criteria — rather than either skipping the milestone
entirely or rebuilding things that already work — is the honest middle path.

**Interview angle.** *"Why not just mark M17 done automatically once M15 and M16 shipped, since they
covered most of it?"* Because "the pieces exist" and "the page works as one coherent whole, including
on a phone" are different claims — M17's actual job was verifying the second claim, not just checking
that the first one's ingredients were present.

### Review questions

1. **Read the code.** `SummaryCard` filters out any row whose `value` is `null` before rendering.
   Trace through what the card looks like when `sender`, `deadline`, and `amount` are *all* null —
   confirm it matches `ExtractionSummary`'s empty-state pattern from M9, and explain why silently
   rendering nothing (rather than an empty card with three dashes) is the more honest choice here.
2. **Design.** Mobile-readiness was verified with one synthetic viewport check
   (`scrollWidth`/`clientWidth` at 375px). What's the concrete gap between that and the DoD's real
   requirement, "works on my phone" — and is that gap actually closed anywhere in the milestone plan,
   or still open?
3. **Practice.** The header rename ("Extracted text" → "Your letter") is a one-line change with no
   test coverage anywhere. Why is that an acceptable gap for this specific change, when the same
   absence of tests would be a real problem for, say, `readability.py`'s Flesch score formula?

### Teach-back

> **"Sometimes the honest version of 'is this milestone done' is admitting most of it was already done."**
Explain why treating M15 and M16 as having quietly satisfied most of M17's requirements — rather than
either padding the milestone with unnecessary new work to make it feel substantial, or skipping it
outright — is the more defensible engineering call, and what that says about writing a milestone plan
before the incremental order of implementation is fully known.

---

## M18 — Document viewer: raw scan, coordinate normalization *(done)*

### Plan Gate

**What.** Before M18, raw upload bytes never survived past the OCR call that consumed them — nothing
existed to render. New `DocumentStore` persists them; a new `GET /jobs/{id}/pages/{n}` reuses
`ingestion.rasterize()` (OCR's own first step) to serve the RAW, un-preprocessed page as PNG.
Frontend `DocumentViewer` renders it, plus a permanent, non-interactive proof-of-concept overlay
(using real `source_span` data already on the frontend) demonstrating the coordinate math M19 will
need.

**Files touched.** New `backend/app/repositories/document_store.py`; `backend/app/api/jobs.py` (new
endpoint); `backend/app/services/job_service.py` (`document_store` wiring); new
`frontend/src/lib/bbox.ts`, `frontend/src/components/DocumentViewer.tsx`;
`frontend/src/services/api.ts` (`getDocumentPageUrl`); `frontend/src/app/result/[id]/page.tsx`;
`docs/adr/0008-document-viewer-serves-raw-rasterized-pages.md`.

**The trade-off.** Serving the raw rasterized image (what the user recognizes as their letter)
versus the OCR-preprocessed one (grayscale/deskewed — what every `BBox` is actually computed
against, guaranteeing pixel-exact overlay alignment). Chose raw, for M18's literal story ("see the
original scan") — and named the alignment gap explicitly as an open question for M19 rather than
silently assuming it away. Full reasoning in ADR-0008.

### Decisions log

#### D42 — The raw page image is re-rasterized on request, not cached at upload time

**What.** `GET /jobs/{id}/pages/{n}` calls `ingestion.rasterize()` fresh on every request, from the
stored raw bytes — it does not pre-render and cache PNGs when the job is created.

**Why.** Simplicity first, matching this project's own "walking skeleton, optimize later" posture
(the same one that shipped M2's in-memory job store before ever discussing Postgres). Most letters
are 1-3 pages; re-rasterizing on each of a handful of requests is cheap relative to the OCR pass
that already happened on the same bytes, and standard HTTP caching (the browser's own cache for a
repeated `<img>` request) already avoids most redundant work without any server-side cache to keep
correct.

**Interview angle.** *"What would make you add server-side caching here?"* Evidence, not
anticipation — real usage showing this endpoint is actually hit often enough, on large enough
documents, for re-rasterization cost to matter. Caching a value that's cheap to recompute and rarely
requested is complexity spent on a problem that doesn't exist yet.

#### D43 — `DocumentStore` is a separate boundary from `JobRepository`, not a field on `Job`

**What.** Raw bytes live in their own store, looked up by job ID through `JobService.get_document()`
— they are never part of the `Job`/`JobResult` Pydantic models that get serialized to JSON on every
poll.

**Why.** Same separation-of-concerns argument ADR-0004 already made for embedding `BBox`es directly
in `SourceSpan` rather than requiring a second lookup — just pointed the other way here: some data
belongs *with* the record (small, always needed, JSON-native) and some belongs *behind* a separate
lookup (large, binary, needed only when explicitly requested). Putting raw file bytes on `JobResult`
would mean every single poll response — dozens of them, at `POLL_INTERVAL_MS = 1200`, for the
duration of processing — carries a multi-megabyte payload nothing but the document viewer ever
reads.

**Interview angle.** *"Why not base64-encode the image into the JSON response instead of a separate
binary endpoint?"* Base64 inflates binary data by roughly a third and forces the whole payload to be
re-fetched on every poll instead of once, cached by the browser like any other image request — a
dedicated binary endpoint is both smaller on the wire and only fetched when actually needed.

### Review questions

1. **Read the code.** `get_document_page` calls `rasterize()` with `settings.max_document_pages` and
   `settings.ocr_render_scale` — the exact same settings OCR itself uses. What would visually change
   about the served image if `render_scale` were lowered just for this endpoint, and why might that
   be a reasonable thing to do that this implementation doesn't do yet?
2. **Design.** `DocumentViewer`'s permanent overlay only draws boxes for fields whose `source_span`
   is non-null. Trace through what happens on a letter where extraction ran but zero fields resolved
   a source span (M10's unverified-confidence-cap path) — what does the viewer show, and is that the
   right default given M19 hasn't been built yet?
3. **Practice.** ADR-0008 explicitly defers the deskew-alignment question to M19 "with real evidence
   (how much do real photos actually get deskewed?) instead of a guess made now." What evidence,
   specifically, would need to exist before that decision could actually be made — and does anything
   in this project currently produce it?

### Teach-back

> **"Naming an open question honestly is not the same as leaving it unsolved."**
Explain the difference between ADR-0008 punting on the deskew-alignment problem by never mentioning
it, versus explicitly deciding "raw image for now, here's exactly what would need to be true to
revisit this" — and why the second one is real engineering judgment even though the code does the
same thing either way today.

---

## M19 — Tap a field, see it highlighted *(done)*

### Plan Gate

**What.** `ExtractionSummary` rows become real buttons; tapping one highlights that specific field's
`source_span` in `DocumentViewer` (distinct from M18's permanent faint boxes) and auto-scrolls to
its page. A field with no `source_span` shows a verify-manually prompt instead of a highlight —
there's nothing real to point at.

**Files touched.** `frontend/src/components/ExtractionSummary.tsx` (clickable rows),
`frontend/src/components/DocumentViewer.tsx` (selection, highlight, scroll, prompt),
`frontend/src/app/result/[id]/page.tsx` (new `DoneView` component holding the selection state).

**The trade-off.** Where should "which field is selected" live? `ExtractionSummary` and
`DocumentViewer` are siblings in the render tree — neither can hold state the other needs to react
to. Chose to lift it into their nearest common parent, which meant extracting the "done" case out of
`renderState` (a plain function, not a component) into a real component (`DoneView`) that can call
`useState`. The alternative — reaching for a context provider or a state library — would be real
over-engineering for one piece of state shared between two components three lines apart in the JSX.

### Decisions log

#### D44 — `renderState`'s "done" case became a component specifically because it needed a hook

**What.** `DoneView` didn't exist before M19; `renderState`'s switch statement built the "done" JSX
inline. It was pulled out into its own function *only* because `useState` needed a real component to
attach to — `renderState(state)` is called directly (`renderState(state)` in JSX, not
`<RenderState state={state} />`), so React never tracks it as a component instance, and ESLint's
rules-of-hooks would (correctly) flag a hook inside it.

**Why.** This is a case where a lint rule caught a real architectural question before it became a
bug: putting `useState` in a function React doesn't render as a component wouldn't necessarily error
immediately, but it would behave unpredictably across re-renders (hook state tied to call-site
position in the *parent's* hook list, not a stable identity of its own) the first time `renderState`
was called conditionally or the switch branched differently between renders.

**Interview angle.** *"Why not just move the whole switch statement into a component instead of
extracting only the 'done' case?"* Only one branch needed state — `loading`/`processing`/
`low_quality`/`failed`/`error` are all stateless renders of already-known data. Converting the whole
switch would work, but it's a bigger diff for the same result; extracting exactly the branch that
needed a hook is the smaller, more legible change.

#### D45 — The permanent overlay (M18) and the selected highlight (M19) are visually distinct, and both stay

**What.** Every field with a `source_span` still gets M18's faint, static box. The newly-selected
field gets a *second*, brighter, animated box drawn on top of it.

**Why.** Removing the permanent overlay in favor of only-on-click boxes was considered and rejected:
the faint boxes are a passive trust signal ("here's everywhere we found something"), while the
bright pulsing one is an active answer to "show me *this specific* one." Collapsing them into one
visual language would lose the passive signal for users who never click anything at all.

**Interview angle.** *"Two overlapping absolutely-positioned overlays on the same element — how do
you know the z-order and pointer-events don't fight each other?"* Both boxes use
`pointer-events-none`, so neither can intercept clicks meant for the image or the page underneath;
the brighter box is simply rendered after the faint ones in DOM order, which is sufficient for
correct stacking without an explicit `z-index` since they share the same stacking context.

#### D46 — The verify-manually prompt is a real design decision, not a placeholder for "nothing to show"

**What.** Selecting a field with `source_span: null` doesn't just leave `DocumentViewer` unchanged
— it renders an explicit `role="status"` message naming the situation.

**Why.** Silence would be ambiguous: did the click register? Is something loading? Is this field
just not verifiable? An explicit message answers all three at once, and does it in the same honest
register as every other unverified-value signal in this codebase (the amber "unverified" badge in
`ExtractionSummary`, the readability/advice-linter flags in `ExplanationCard`) — a consistent visual
vocabulary for "we're telling you what we don't know," not a one-off.

### Review questions

1. **Read the code.** `DocumentViewer`'s `pageRefs` is a `useRef<Map<number, HTMLDivElement>>`, populated
   via a callback ref that adds or deletes an entry on every render. Why a `Map` keyed by page number
   instead of an array indexed by page, given `pageCount` is already known up front?
2. **Design.** The selected-field highlight and the low-quality gate's withheld-text rule (M6, D14)
   both refuse to show something the pipeline isn't confident about. Compare them: is
   "don't highlight an unverified field" as strong a trust guarantee as "don't show low-confidence
   OCR text," or is there a meaningful difference in what each one is actually protecting the user
   from?
3. **Practice.** `DoneView`'s `useEffect` scrolls to a page whenever `selectedSpan` changes, keyed
   only on `[selectedSpan]`. Construct a scenario where clicking the *same* field twice in a row
   would (or wouldn't) re-trigger the scroll, and explain why that's the correct behavior given how
   object identity works in the dependency array.

### Teach-back

> **"A highlighted box and a 'please verify manually' message are the same feature, pointed at two different truths."**
Explain why M19 treats "this field is exactly here" and "we genuinely don't know where this field
is" as two outcomes of one interaction, rather than only building the happy path and leaving the
unverified case to fail silently — and connect it to why that mirrors the extraction pipeline's own
null-not-guess discipline one layer up, in the UI instead of the data.

---

## M20 — Regression tests for the whole journey *(done — closes Sprint 3)*

### Plan Gate

**What.** Two genuinely new pieces of test infrastructure, not incremental additions to existing
suites: `test_full_pipeline_e2e.py` (backend) proves classification, extraction, and explanation
all stay correctly wired together in one real-OCR job — something no existing e2e test covered.
`e2e/happy-path.spec.ts` is the project's first Playwright test — a frontend smoke test of the
actual rendered app, not components in isolation.

**Files touched.** New `backend/app/tests/test_full_pipeline_e2e.py`; new
`frontend/playwright.config.ts`, `frontend/e2e/happy-path.spec.ts`; `frontend/package.json`
(`@playwright/test`, `test:e2e` script); `.github/workflows/ci.yml` (2 new frontend steps);
`.gitignore` (Playwright artifact directories).

**The trade-off.** Mock every backend call in the Playwright spec versus running it against a real
backend (with real or stubbed Tesseract/Gemini) in CI. Chose mocking, deliberately: a frontend smoke
test's job is proving the *rendering and interaction logic* works given a known API shape, not
re-proving the pipeline itself works — that's what the backend's own e2e tests are for. Mocking also
means this test costs nothing and needs nothing running except the frontend's own dev server, in
CI or locally.

### Decisions log

#### D47 — The full-chain test asserts on data crossing between steps, not just that each step ran

**What.** `test_the_whole_pipeline_stays_correctly_wired_together` doesn't just check that
`doc_type`, `extraction`, and `explanation` are each non-null — it checks that `sender.source_span`
was found (proving extraction ran against the *same* real `OcrDocument` OCR produced) and that the
explanation text actually contains "Finanzamt" (proving it was grounded in that same extraction,
not a disconnected canned string).

**Why.** A weaker test — "each of these four fields is populated" — could pass even if a future
refactor accidentally ran extraction against stale OCR output, or explanation against a different
job's extraction. Asserting on data that had to *flow* from one step to the next is what actually
catches a wiring regression; asserting presence alone only catches a step being skipped entirely.

**Interview angle.** *"Isn't checking `"Finanzamt" in explanation.text` a fragile assertion tied to a
specific fake's wording?"* Yes, deliberately — the fake explainer's text was chosen specifically to
make grounding checkable this way. A fragile-but-meaningful assertion beats a robust-but-vacuous one
here; the alternative (checking `explanation.text` is merely non-empty) would pass even if
explanation silently stopped receiving the extraction at all.

#### D48 — The Playwright spec mocks the network layer, not the React component tree

**What.** Every backend interaction is intercepted at the `page.route()` level (real `fetch` calls,
fake responses) — nothing is mocked inside the React components themselves, and no component is
rendered in isolation outside the actual Next.js app.

**Why.** Mocking at the network boundary means the test exercises the real `services/api.ts`
functions, the real polling loop in `page.tsx`, and the real conditional rendering logic in
`DoneView` — the exact code that ships to production, with only the one true external dependency
(the backend) replaced. Mocking deeper (e.g., swapping out `getJob` itself) would leave gaps between
what the test proves and what a real user's browser actually does.

**Interview angle.** *"Why not just run this against your real dev backend in CI instead of mocking
it?"* Determinism and cost: a real backend needs Tesseract installed in the CI image and either no
AI key (making extraction/explanation always null, defeating the point of testing the full UI) or a
real Gemini key spending real (if free-tier) quota on every CI run — this session's own quota
exhaustion is a live example of exactly that fragility. Mocked responses are instant, free, and
never flake because of an external service's availability.

#### D49 — A racy assertion on a transient UI state was fixed by giving it its own test, not by adding a wait

**What.** The first version of the happy-path spec asserted `"Reading your letter…"` was visible
mid-flow, in the same test that also asserted the terminal "done" state — and failed intermittently,
because the mocked poll could resolve to "done" before that assertion's turn ran. The fix wasn't a
longer timeout or an artificial delay; it was moving the processing-state assertion into its own
test, with a mock that *never* resolves to a terminal status.

**Why.** Adding a `waitForTimeout` or similar would have "fixed" the flake by making the test slower
and still fundamentally racy — a transient state that's *supposed* to disappear quickly is the wrong
thing to assert on in a test that also lets it disappear. Testing it properly meant controlling the
mock so that state is stable for the whole test, not chasing a moving target with a longer clock.

**Interview angle.** *"How do you tell a flaky test caused by a real bug apart from one caused by bad
test design?"* Here, the app's behavior was correct the whole time — the poll really did transition
states exactly as designed. The flake was entirely in the test's assumption that a transient state
would still be visible by the time an assertion got around to checking it. The tell: fixing it
required changing the *test's* control over time/state, not the application code.

### Review questions

1. **Read the code.** `test_full_pipeline_e2e.py`'s `_fake_explainer` ignores its `extraction`
   argument entirely and returns a fixed string. Why is that acceptable for this test's purpose,
   given D47 says the test needs to prove real data flows between steps?
2. **Design.** The Playwright config sets `retries: process.env.CI ? 2 : 0`. Given D49's root cause
   (a mock resolving faster than an assertion could run), would retries have actually masked that
   bug instead of the fix that was made — and what does that imply about when retries are a
   reasonable safety net versus a way to hide a real race?
3. **Practice.** This closes Sprint 3 (M15–M20). Across those six milestones, name one thing that
   was true of the *first* milestone in the project (M1) that is still true now, and one thing about
   how work gets verified that has genuinely changed.

### Teach-back

> **"Two different kinds of 'the whole thing works' — proving the pipeline stays wired together, and proving the UI carries a real user through it — are not the same test, and neither one is optional."**
Explain why `test_full_pipeline_e2e.py` (backend, real OCR, mocked AI) and `happy-path.spec.ts`
(frontend, mocked everything) each catch a category of regression the other one structurally cannot
— and why M20 needed both rather than treating one as sufficient coverage for "the full journey."

---

## Sprint 3 review, and M21

Sprint 3 (M15–M21) closes with M20 above. M21 ("a real non-native user can complete the whole
journey on their phone without getting confused") needs 2 real human testers on real phones —
fundamentally not something Claude can simulate or fabricate without producing a fake "friction
point" that would look like real evidence while being false, the same principle as D15's
golden-letter rule. `docs/m21-phone-test-script.md` is the buildable part (recruiting guidance, a
deliberately hands-off task list, a friction-log template, guidance for turning results into a
top-3 fix list) — `PROGRESS.md` marks M21 **blocked**, not done and not skipped. Following M13's own
precedent (a purely-blocked milestone with zero code gets no full Decisions/Review/Teach-back
section here), M21 gets none either — there's no code to review questions about yet. Sprint 4 begins
at M22 below.

## M22 — One-click delete + 24h auto-purge *(done)*

### Plan Gate

**What.** Two things, cleanly separable: (1) a user-triggered `DELETE /jobs/{id}` that removes a
job and its raw document bytes on request, and (2) a time-triggered background sweep that removes
*anything* past a 24h retention window, whether or not the user ever asks — the actual privacy
guarantee, since most users won't click delete. Both close a gap ADR-0008 named explicitly: M18's
`DocumentStore` made uploaded bytes persist in-memory for the process's lifetime with no expiry.

**Files touched.** `repositories/job_repository.py` + `repositories/document_store.py` (new
`delete()`, `list_all()` on the job repo only); new `services/retention.py` (pure `purge_expired()`);
`services/job_service.py` (`delete_job()`, `purge_expired()` wrappers); `api/jobs.py` (`DELETE
/jobs/{id}`); `config/settings.py` (`retention_max_age_hours`, `retention_sweep_interval_seconds`);
`main.py` (FastAPI `lifespan` running the sweep as a background `asyncio.Task`); new
`frontend/src/components/DeleteButton.tsx`; `services/api.ts` (`deleteJob`); `app/result/[id]/page.tsx`
(wiring); new `e2e/delete.spec.ts`. ADR-0009.

**The trade-off.** The sweep's scheduling mechanism versus everything else that could run periodic
work: a cron job, an external task queue (Celery/RQ + a broker), a scheduled cloud function, or a
dedicated scheduling library (APScheduler). Chose an `asyncio.Task` started in FastAPI's own
`lifespan`, with a plain `while True: await asyncio.sleep(...)` loop. It costs nothing new (no
process, no dependency, no deploy target) and lives exactly as long as the app server the
zero-cost/local-first strategy (ADR-0001) already runs — but it means the retention guarantee is
tied to the app process's uptime, and a process restart resets the sweep's *timer* (though not any
job's actual age, since `created_at` lives on the `Job` record itself, not on the sweep's clock).

### Decisions log

#### D50 — `delete()` returns whether something was deleted; `DocumentStore.delete()` doesn't

**What.** `JobRepository.delete(job_id) -> bool` reports found-and-removed vs. already-absent. The
new `DocumentStore.delete(job_id) -> None` doesn't — it's unconditionally idempotent, silently a
no-op if nothing was there.

**Why.** The two stores have different callers with different needs. The `DELETE /jobs/{id}`
endpoint needs to answer 204 vs. 404, and the job repository's `bool` return gives it that for free,
without a separate `get()` round-trip first. Nothing downstream ever needs to know whether document
bytes specifically existed — `JobService.delete_job()` always tries to delete from both stores
regardless, and the retention sweep calls `document_store.delete()` for every expired job id whether
or not that job happened to have document bytes stored (e.g., a job that failed before `create_job`'s
`document_store.put()` ever ran, in a hypothetical future ordering). Giving both methods the same
signature "for consistency" would mean either faking a boolean nobody reads, or making the sweep do
an unnecessary existence check first.

**Interview angle.** *"Isn't an inconsistent interface across two structurally similar stores a code
smell?"* Only if the inconsistency is accidental. Here it tracks a real difference in how each
return value gets used — `JobRepository.delete()`'s boolean drives an HTTP status code; nothing
analogous exists for document bytes. Matching signatures for their own sake, when the callers'
actual needs differ, would be the smell.

#### D51 — Delete verification happens on the client too, not just the server

**What.** `DeleteButton` doesn't show "Deleted" the moment `DELETE` returns 204. It immediately
calls `getJob()` again and only shows the success message once *that* returns a 404.

**Why.** CLAUDE.md §5.6's bar is "one-click delete verified at storage layer" — the backend tests
(`test_delete_removes_the_job_and_a_subsequent_get_returns_404`) already prove the server side. But
the user-facing claim "this is really gone" deserves the same discipline the rest of this codebase
applies to every other trust claim (M10's source-span linking, M11's validators, M19's verify
prompt): don't just trust that an action succeeded because the API call didn't throw — confirm the
consequence actually took effect before telling the user it did.

**Interview angle.** *"Doesn't this double the number of requests for every delete, for a check that
should always pass if the backend is correct?"* Yes, deliberately, for one specific action: this is
the one operation in the whole app whose entire value proposition is "I can trust that this
happened." A wrong 204 (a proxy caching it, a bug, a race) would otherwise show a false "deleted"
message with nothing to ever contradict it — the user has no other way to find out. Every other
mutation in this app (create job) is already followed by polling that would surface an inconsistency
naturally; delete has no such follow-up, so this check *is* that follow-up.

#### D52 — The confirm step is two clicks, not a modal, not one unconfirmed click

**What.** `DeleteButton` has three UI stages: idle → confirming (inline, same component, no
overlay) → deleted. Clicking "Delete my document" doesn't delete anything; it reveals "Yes, delete
it" / "Cancel" in place.

**Why.** M22's story literally says "in one click," but a single unconfirmed click on a
data-destroying action is a bad interaction regardless of what the story's headline says — a
misplaced tap on a phone (the primary device this app targets, per M7/M21) shouldn't silently
destroy the only record of a real government letter. An inline two-stage confirm keeps the
*decisive* action (the actual delete) to one click, without a modal's extra weight, while still
requiring one deliberate additional tap to get there.

**Interview angle.** *"How would you decide whether an action needs this kind of confirm step at
all?"* Reversibility and blast radius: irreversible + high-consequence (delete a user's only copy of
their document, or the "publish"/"send" family of actions) gets a confirm; reversible or
low-consequence (toggling a UI state, navigating) doesn't. This is the same framework this session
already applies to its own tool-use decisions — the parallel isn't a coincidence.

### Review questions

1. **Read the code.** `services/retention.py::purge_expired()` takes `now` and `max_age` as
   parameters rather than calling `datetime.now(UTC)` internally. Given `main.py`'s sweep loop is the
   only real caller, why does that matter enough to be worth the extra two parameters at every call
   site, including the tests?
2. **Design.** `JobRepository.list_all()` was added purely so the retention sweep can find expired
   jobs, and it's noted in ADR-0009 as something a real (non-in-memory) implementation should replace
   with an indexed query. What would that indexed query look like, and what does `list_all()` cost
   today that it wouldn't cost against a real Postgres-backed repository?
3. **Practice.** `main.py`'s `_retention_sweep_loop` wraps its purge call in a bare `except Exception`
   that only logs. Compare this to how `JobService._process` handles classification/extraction/
   explanation failures (also caught, also logged, never re-raised) — what property do all four of
   these best-effort blocks share, and what would break if the sweep loop let an exception propagate
   instead?

### Teach-back

> **"A privacy feature that can't prove its own effect isn't a privacy feature — it's a claim."**
Explain why `DeleteButton`'s re-fetch-and-confirm-404 step (D51) exists even though the backend
already has its own passing tests for the same behavior, and connect it to why CLAUDE.md's rule is
"privacy claims = implementation" rather than "privacy claims = intent."

---

## M23 — Privacy page, written from the code, not around it *(done)*

### Plan Gate

**What.** A static `/privacy` page, plus links to it from the landing page and every result page.
The actual work wasn't writing generic privacy boilerplate — it was going back through M22's real
implementation line by line and stating only what's literally true of it: in-memory-only storage
(not "encrypted at rest," there's no "rest"), an hourly sweep against a 24h ceiling (not "instantly
at 24h"), and a genuine third-party disclosure — the letter's OCR'd text is sent to Google's Gemini
API — that a generic privacy template would have no way to know needed saying at all.

**Files touched.** New `frontend/src/app/privacy/page.tsx`; `app/page.tsx` (footer link, tagline
reworded); `app/result/[id]/page.tsx` (footer link); new `e2e/privacy.spec.ts`.

**The trade-off.** A privacy *page* versus a privacy *section* folded into an existing page (e.g. a
collapsible block on the landing page). Chose a separate route: `/privacy` is something a user might
want to link to, bookmark, or read before ever uploading anything — folding it into the landing page
would make it compete for attention with the upload form, exactly the pattern a real privacy notice
shouldn't have to fight against to be read.

### Decisions log

#### D53 — The Gemini disclosure is written as a warning, not a footnote

**What.** "What leaves this server" is its own section, stated in the second sentence as "a real
third party seeing the content of your letter, and you should know that before uploading something
sensitive" — not buried after the reassuring "no accounts, no tracking" claims.

**Why.** CLAUDE.md §5.6 requires the privacy page to match the code, and the code's honest answer is
that a government letter's actual text — someone's tax bill, an immigration deadline, a fine amount
— leaves this server and reaches a third party's API. A privacy page that led with reassurance and
mentioned this only in passing would be technically true and practically misleading, which is worse
than omitting it entirely because it *looks* thorough while still failing the actual goal: a user
making an informed decision before uploading.

**Interview angle.** *"Isn't over-disclosing a real risk too — scaring users off a genuinely private-
enough system?"* The bar CLAUDE.md sets isn't "make users comfortable," it's "match what the code
does." If disclosing something true makes a reasonable user hesitate, that's information the system
correctly gave them, not a UX failure to smooth over. The alternative — softening a true statement
so it reads better — is exactly the failure mode "privacy claims = implementation" exists to rule
out.

#### D54 — "In-memory, not on disk" is stated as a consequence, not a feature

**What.** The storage section doesn't say "we auto-delete after 24 hours" and stop there. It leads
with the fact that nothing is written to a database or disk at all, and explicitly says a server
restart clears everything *before* the 24h window would have.

**Why.** Stopping at "auto-deleted within 24h" would describe the *ceiling* without mentioning the
system also has no floor — in practice, given a demo-scale single process with no persistent
volume, most documents disappear far sooner than 24h, on the next redeploy or crash. Saying only the
ceiling implies a guarantee ("your data is definitely kept for up to 24h") that the actual
architecture doesn't provide and was never designed to provide. This is the same instinct as ADR-0009
naming its own approximation (hourly sweep vs. exact-24h) explicitly rather than rounding it away.

**Interview angle.** *"Why is 'less retention than promised' worth calling out, when most privacy
complaints are about systems keeping data too long, not too short?"* Because the standard being held
to isn't "is this good for privacy" (a shorter, less predictable retention window trivially is) —
it's "does this page accurately describe the system." An inaccurate claim in the *more*
privacy-protective direction is still an inaccurate claim; a user who assumes their document will be
retrievable for a day and finds it isn't has been told something false, even though the falseness
favored them this time.

### Review questions

1. **Read the code.** `PrivacyPage` is a server component (no `"use client"` directive) that renders
   entirely static content. `DeleteButton` and `ConnectionStatus`, by contrast, both need
   `"use client"`. What's the actual mechanical reason one needs it and the others don't, and what
   would break (or just get slower) if `"use client"` were added to `PrivacyPage` unnecessarily?
2. **Design.** The Gemini disclosure names "classify, extract, and explain" as what the text is sent
   for, but doesn't name Tesseract as also processing the letter, even though Tesseract reads the
   actual image. Is that omission correct given the "What leaves this server" section's actual scope,
   or is it a gap the page should close?
3. **Practice.** `e2e/privacy.spec.ts` asserts on `page.getByText(/Google's Gemini API/)` — text
   copy, not a `role`/`aria` attribute like most of this project's other Playwright assertions. What
   does pinning an e2e test to exact prose cost the next time this page's copy gets edited, and is
   that cost worth what the test is actually protecting against here?

### Teach-back

> **"A privacy page's job is to be falsifiable — every sentence on it should be something you could point at a line of code to check."**
Explain why `/privacy` was written by reading `services/retention.py`, `main.py`'s sweep loop, and
`GeminiService` first, rather than by writing a standard privacy-policy template and then checking
it roughly matched — and what CLAUDE.md means by "privacy claims = implementation" that a generically
accurate-sounding privacy page would still fail.

---

## M24 — Hardening: rate limiting, streaming size guards, request logging, prompt-injection defense *(done)*

### Plan Gate

**What.** Four real pieces of hardening, one honest non-decision: an in-memory per-IP rate limiter
on the two state-changing endpoints; upload reads switched from one unbounded `await file.read()` to
bounded chunked reads that reject an oversized body without ever fully receiving it; a structured
`http_request` log line per request through the existing M1 structlog pipeline; and a
prompt-injection guardrail (delimiter + explicit instruction) wired into all three LLM prompts. The
milestone plan's fifth item, an uptime monitor, was deliberately not built — there's no hosted
deployment to watch (ADR-0001), so one would have nothing real to monitor.

**Files touched.** New `services/rate_limiter.py`, `services/ai/prompts/__init__.py` (was empty);
`api/jobs.py` (`_read_bounded`, `enforce_rate_limit`, wired onto both routes); `main.py`
(`log_requests` middleware); `config/settings.py` (`rate_limit_*`); `services/ai/prompts/classify.py`
/ `extract.py` / `explain.py` (delimiter + instruction wired in); new `tests/conftest.py`,
`test_rate_limiter.py`, `test_rate_limit_api.py`, `test_request_logging.py`, `test_prompts.py`;
`test_jobs.py` (streaming-read test). ADR-0010.

**The trade-off.** How far "guardrails" should go for a pipeline that sends user-uploaded content to
a third-party LLM: a dedicated prompt-injection classifier (a second LLM call screening input before
the real one) versus a cheap, static defense (delimit the content, instruct the model not to treat it
as instructions). Chose the cheap option deliberately — not because it's a complete defense (it
isn't; a sufficiently motivated injection could still work), but because the real security boundary
in this pipeline was never the prompt. It's the deterministic output-side checks
(`validators.py`, `advice_linter.py`) that already don't trust the model's compliance with anything
it was asked to do. A classifier call would add cost and a new attack surface of its own for a
defense that isn't where this app's actual guarantees live.

### Decisions log

#### D55 — Chunked reads bound *received* bytes, not just *accepted* bytes

**What.** `_read_bounded` reads the upload in 1 MiB chunks and stops the moment the running total
exceeds `max_upload_bytes`, instead of the previous `await file.read()` (which reads to EOF
regardless of size, then checks the length of what it got).

**Why.** The old code's size check was real but late: a client sending a 5 GB body would have all 5
GB received (and, past Starlette's `SpooledTemporaryFile` threshold, spooled to disk) before the
`len(contents) > max_upload_bytes` check ever ran. Neither FastAPI nor Starlette enforces a body-size
cap on its own. Reading in bounded chunks means the worst case is `max_upload_bytes` plus one chunk,
no matter what the client sends or claims — the guard now bounds *received* data, not just what gets
*accepted* afterward.

**Interview angle.** *"Doesn't checking the `Content-Length` header up front make more sense than
reading chunk-by-chunk?"* `Content-Length` is client-supplied and not authoritative — a client can
lie (send a small declared length, then keep streaming), and some clients/proxies omit it
(chunked transfer-encoding) or the ASGI server may not always populate it as a header available at
this layer for every transport. Bounding the actual read is correct regardless of what the client
claims; a `Content-Length` check would be a nice-to-have fast-path rejection on top of this, not a
substitute for it.

#### D56 — The rate limiter's test isolation problem mirrored M10's dependency-override bug, one layer up

**What.** `get_upload_rate_limiter()` is `@lru_cache`'d, exactly like `get_job_service()`. Left
unaddressed, that singleton's accumulated hit history would persist across the *entire pytest
session* — dozens of unrelated tests issuing `POST`/`DELETE /jobs` from the same TestClient "IP"
would eventually trip the real 20/min limit and start failing with 429s that have nothing to do with
what they're testing. Fixed with a new `conftest.py` autouse fixture that calls
`get_upload_rate_limiter.cache_clear()` before every test, giving each one a fresh, empty-history
limiter.

**Why.** This is the same root cause as the M10 dependency-override bug (a cached singleton with
mutable state, shared across everything that resolves it) — just manifesting as cross-*test*
pollution instead of cross-*request* staleness within one test. Recognizing the pattern meant the fix
took minutes instead of chasing down mysterious, order-dependent 429s across the suite later.

**Interview angle.** *"Why `cache_clear()` in a shared fixture instead of overriding
`get_upload_rate_limiter` per test, the way `get_job_service` gets overridden everywhere else?"*
Because most tests don't care about rate limiting at all — it's incidental to what they're testing.
Requiring every test file that happens to call `POST /jobs` to also remember to stub out rate
limiting would be exactly the kind of "you have to know an unrelated implementation detail to write a
passing test" trap this project has consistently avoided (see M10's own post-merge fix). A shared
autouse fixture makes the default safe without every test author needing to think about it;
`test_rate_limit_api.py` is the one place that deliberately opts back into real enforcement, with its
own small dedicated limiter instance.

#### D57 — The prompt-injection defense is named honestly as partial, in the ADR and in code comments

**What.** ADR-0010 and `services/ai/prompts/__init__.py`'s own docstring both say outright that
`wrap_untrusted_content()`/`UNTRUSTED_CONTENT_INSTRUCTION` reduce risk, not eliminate it — and that
`validators.py`/`advice_linter.py` remain the real backstop, unchanged by this milestone.

**Why.** It would be easy to write this feature as "prompt injection: fixed" in `PROGRESS.md` and
move on. That's not true, and CLAUDE.md's own posture throughout this project — null-not-guess,
"don't just ask nicely, verify," honest failure analysis over polished claims — is exactly the
standard that rules out overstating what a prompt-level instruction can guarantee. A model can be
argued out of following an instruction; it's much harder to argue a Pydantic schema validator or a
regex-based advice-phrase linter out of catching what it's built to catch.

**Interview angle.** *"If you know a defense is incomplete, why ship it at all?"* Because
defense-in-depth means each layer catches what the layers around it miss, not that any single layer
has to be airtight alone. The delimiter/instruction layer costs nothing and closes off the *laziest*
injection attempts (ones that don't even try to survive a sanitization step); the output-side
validators catch what actually reaches the model's response regardless of whether the input-side
defense held. Shipping the cheap layer while being honest about its limits is a stronger
engineering posture than either skipping it (why leave free defense on the table?) or overselling it
(why claim more than what's actually true?).

### Review questions

1. **Read the code.** `RateLimiter.allow()` takes `now` as a required keyword argument, and
   `allow_now()` is a thin wrapper that supplies `time.monotonic()`. `services/retention.py::
   purge_expired()` takes an analogous `now` parameter. What do these two clock-injection patterns
   have in common, and why does `time.monotonic()` specifically (not `time.time()`) matter for the
   rate limiter in a way it wouldn't for the retention sweep's `datetime.now(UTC)`?
2. **Design.** `enforce_rate_limit` is applied per-route via `dependencies=[Depends(enforce_rate_limit)]`
   rather than as global middleware covering every endpoint. `GET /jobs/{id}` and
   `GET /jobs/{id}/pages/{n}` are *not* rate-limited. Is that a gap, or a deliberate scope decision —
   and what's actually different about a polling `GET` versus an upload `POST` that would justify
   treating them differently under an abuse model?
3. **Practice.** `test_prompts.py` asserts that `UNTRUSTED_CONTENT_INSTRUCTION` is a substring of
   each system instruction, and that `wrap_untrusted_content()`'s delimiter appears in each user
   message. Given D57 says this defense can't be proven to work against a real model, what is this
   test suite actually proving, and is it worth having anyway?

### Teach-back

> **"Some defenses are worth shipping even when you can't prove they work — as long as you don't pretend they do."**
Explain the difference between `wrap_untrusted_content()`/`UNTRUSTED_CONTENT_INSTRUCTION` (a
best-effort, unprovable input-side mitigation) and `validators.py`/`advice_linter.py` (a
deterministic, fully-tested output-side guarantee) — and why ADR-0010 was written to name that
difference explicitly rather than letting "we added prompt-injection guardrails" stand as an
unqualified claim in `PROGRESS.md`.

---

## M25 — Eval on 30 golden letters *(blocked, no code)*

Same blocker as M12/M13, and the same handling: `eval/golden/manifest.json` still has 0 real
letters, and cannot be filled with fabricated ones without defeating the entire purpose of the eval
suite (D15). One thing worth recording: `docs/finanzamt_testbrief.pdf`, sitting untracked in the
repo since early in this session, looked at first glance like it might quietly unblock this — a
well-formed, realistic Finanzamt letter. Reading it confirmed its own footer states it's a fictional
test document ("kein echtes Finanzamt-Schreiben"), and the names are transparent placeholders
("Erika Beispiel," "Musterstadt" — literally "Ms. Example," "Model City"). It's a good manual
smoke-test fixture; it is not a golden letter, and using it as one would have produced a scorecard
that looked real while measuring nothing. `eval/run_eval.py` and `scoring.py` (M12) are ready to run
the moment real letters exist. Following M13/M21's own precedent, no full Decisions/Review/Teach-back
section here — there's no code to review questions about.

## M26 — Architecture diagram, portfolio README rewrite *(done)*

### Plan Gate

**What.** `README.md` and `docs/ARCHITECTURE.md` had been untouched since roughly M1 — both still
described Docker Compose + Postgres as the primary way to run the project, and `AIService` with its
old two-operation shape (`extract_document`, `summarize`) from before M15 replaced `summarize` with
`explain_document`. A hiring manager following the old README literally would have hit a stale,
retired `GEMINI_MODEL` in the root `.env.example` and a dev path (Docker) that turned out to have
never actually been the one exercised this entire project. M26's real job wasn't writing new prose —
it was finding out how far the documentation had drifted from the actual system, and closing that
gap honestly rather than polishing around it.

**Files touched.** `README.md` (full rewrite), `docs/ARCHITECTURE.md` (full rewrite, new mermaid
diagram + request-lifecycle walkthrough + "Known deviation: Postgres" section), `.env.example`
(root — fixed the stale `GEMINI_MODEL`), `BACKLOG.md` (new Production Feature row for real Postgres
persistence), `PROGRESS.md` (M26 row, cross-referencing the same gap).

**The trade-off.** Silently rewrite the docs to describe the system as it actually is (drop all
Postgres/Docker mentions) versus keep them and explicitly flag the gap. Chose to flag it: the
Postgres/Docker split is exactly the kind of thing CLAUDE.md's "privacy claims = implementation"
principle generalizes to — *any* claim a doc makes has to match the code, and the honest fix for a
stale claim is to say so, not to quietly delete the evidence it was ever claimed. `docker-compose.yml`
and the Dockerfiles were left in place, not deleted — removing working infrastructure code is a
bigger, more consequential decision than a documentation session should make unilaterally.

### Decisions log

#### D58 — The Postgres gap was discovered by writing the README, not by auditing the code first

**What.** The trigger for finding "no code anywhere reads `Settings.database_url`" wasn't a
dedicated code-quality pass — it was trying to write an honest "how to run this" section and
realizing the Docker instructions couldn't be verified as accurate without checking whether Postgres
was actually load-bearing. It wasn't.

**Why.** Worth naming because it's a real, generalizable lesson: documentation work that insists on
being *checkable* against the actual code (the same discipline M23's privacy page applied) surfaces
real bugs and drift that a purely additive feature milestone might never trip over, because feature
work only exercises the paths it needs. Nobody was importing `database_url`, so nothing ever failed
loudly about it being unused.

**Interview angle.** *"If this gap existed since M2, why did it take until M26 to notice?"* Because
nothing forced it to surface: the in-memory stores worked correctly for every milestone's actual
requirements, CI never touched Postgres, and no test asserted persistence survived a restart (the
opposite, even — M22's tests explicitly rely on in-memory behavior). A stack deviation that doesn't
break anything has no natural trigger to be caught, which is exactly why a documentation pass that
insists on verifying its own claims against the code is worth the time it costs.

#### D59 — Docker Compose was marked "present, not verified," not deleted

**What.** The README's new Docker section states plainly that the Postgres container is unconnected
scaffold and that the path "hasn't been the one actually exercised" — but keeps the files and the
instructions, with a pointer to M28 (the fresh-machine README test) as where this actually gets
re-checked or fixed.

**Why.** Removing `docker-compose.yml`/both `Dockerfile`s outright would be a bigger, more
consequential call than a documentation-focused milestone should make on its own — CLAUDE.md §4
lists Postgres in Docker Compose as a "decided" stack choice, and un-deciding it is exactly the kind
of thing that should go through the owner's review (the "full speed, review later" authorization
covers building and documenting honestly, not silently reversing a stack decision CLAUDE.md itself
calls frozen).

**Interview angle.** *"Isn't leaving broken-ish infrastructure in the repo worse than removing it?"*
Not when it's labeled accurately. The risk documentation is supposed to prevent is someone trusting
something false; a clearly-flagged "present but unverified" section prevents that just as well as
deletion would, while preserving the owner's ability to decide whether Docker gets fixed, replaced,
or removed — a decision this session correctly didn't make unilaterally.

### Review questions

1. **Read the code.** `docs/ARCHITECTURE.md`'s new "Known deviation: Postgres" section says
   `Settings.database_url` is "a dead field nothing reads." Grep the codebase and confirm that for
   yourself — what would you look for to be sure, beyond a literal string search for `database_url`?
2. **Design.** The new README frames in-memory-only storage as accidentally *more* private than the
   24h auto-purge promises (everything's gone on restart, not just after 24h). Is that framing
   honest, or does it risk normalizing an architecture gap by finding a silver lining in it — where's
   the line between "an honest upside" and "spin"?
3. **Practice.** No ADR was written for M26, on the reasoning that documentation-only milestones
   don't clear the bar (same as M16/M17/M23). But discovering the Postgres/CLAUDE.md §4 conflict
   feels closer to an architectural finding than a copy edit. Should that specific finding have its
   own ADR even though the milestone as a whole didn't need one — why or why not?

### Teach-back

> **"A README's job is to be re-derivable from the code at any time — the moment it can't be, it's not documentation anymore, it's historical fiction."**
Explain how writing an honest "how to run this" section surfaced a real, un-caught architecture
deviation (Postgres never wired) that six months of feature milestones didn't — and what that implies
about treating documentation passes as a form of testing, not just writing.

---

## M27 — Full-journey demo script *(partial — recording is the owner's task)*

Video recording needs a real screen-capture tool, which isn't available here — same category of
limit as M21's phone testers. `docs/demo-script-full-journey.md` supersedes the Sprint-1-only script
with a full, timestamped ~3-minute shot list covering everything through M24. Automated screenshot
capture was attempted through the Browser pane tooling but the pane wasn't rendering in this
environment (screenshots kept timing out — a limitation, not a bug in the app); rather than fabricate
stills or claim success, left both the recording and the screenshots to the owner — who, notably, had
already started recording a real take mid-milestone (`Sprint 4 - video/1.webm` appeared on disk while
this work was in progress). No Decisions/Review/Teach-back section — no code, following M13/M21's
precedent.

## M28 — Fresh-environment README verification *(partial)*

### What actually happened

No second physical machine exists in this environment, so "clean machine" became: a genuinely fresh
Python venv, built from nothing already installed, isolated from the populated dev venv every other
milestone's tests ran against. `pip install -r requirements-dev.txt` → ruff/black/isort/mypy/pytest
(245 tests) → `uvicorn` boot → `/health`/`/version` respond — every step exactly as documented, zero
silent deviation needed to make it work.

That surfaced two real gaps, both fixed in the same README:

1. **`make` was assumed available without qualification.** It isn't, on Windows, by default — a
   standing Known Deviation on the owner's own machine that the README itself had never actually
   accounted for. Added a one-line caveat pointing at the individual commands, mirroring what the
   `Makefile`'s own top comment already says.
2. **The Tesseract Windows install step didn't mention selecting the German language pack.** Without
   it, `OCR_LANGUAGE=deu+eng` (the actual default) would silently produce garbage on every umlaut and
   ß — a newcomer would get a running app that quietly mis-reads every real German letter, with no
   error anywhere to point at why.

**What didn't get the same treatment.** A parallel isolated frontend check was attempted (copying
`frontend/` minus `node_modules` to run `npm ci` fresh) and aborted — the naive `cp -r` pulled in the
*existing* 400MB+ `node_modules` before the exclusion could apply, and continuing risked disrupting
the owner's own live `npm run dev` session running from that exact directory mid-recording. Frontend
correctness here rests on it having built/linted/e2e-tested clean repeatedly across M20, M22, M23,
and M26 from the same lockfile — real evidence, just not from a freshly-isolated copy the way the
backend check was. Marked **partial**, not **done**, specifically because of that asymmetry: a
milestone whose whole point is "prove this reproduces cleanly" shouldn't quietly claim more certainty
for the frontend than it actually earned this pass.

### Decisions log

#### D60 — A gap that survives 27 milestones of use isn't necessarily rare — it's usually just unexercised

**What.** Both real findings (`make` availability, the Tesseract language pack) are things every
single person who has run this project so far — the owner, across dozens of sessions — already knew
how to work around without ever writing it down, because they'd hit it once, fixed it locally, and
moved on.

**Why.** This is the same shape of finding as M26's Postgres discovery: gaps that don't block the
person who already knows the workaround are invisible to that person's own testing, no matter how
many times they run the project. The only thing that reliably surfaces them is literally starting
from nothing and refusing to silently apply tribal knowledge — which is exactly what a fresh venv
(and, ideally, a fresh machine) forces.

**Interview angle.** *"If the owner already knew both of these, were they really bugs?"* Yes, for the
audience this milestone is actually about — CLAUDE.md frames M26–M28 as being for a *hiring manager*
or a *new developer*, not the owner. A gap the owner has memorized around is invisible to her own
usage and still completely blocking for anyone else, which is precisely why "I can follow the README
on a clean machine" is its own milestone instead of being assumed to fall out of the app simply
working.

### Review questions

1. **Read the code.** The fresh-venv test used Python 3.14, not the README's stated "Python 3.13+."
   `backend/pyproject.toml` pins `target-version = ["py313"]` for black/mypy. Why did running on 3.14
   not surface any failure, and what would have to be true of the codebase for a 3.14-only feature to
   slip in undetected by CI (which — check `.github/workflows/ci.yml` — pins its own version)?
2. **Design.** The frontend check was abandoned specifically to avoid disrupting a live session in
   the same directory. Is "don't touch a directory something else might be using" a good enough
   general rule for when *not* to run a verification step, or does it just mean this kind of check
   needs its own isolated worktree/clone from the start, regardless of what else happens to be
   running?
3. **Practice.** This milestone found real gaps using a fresh *dependency* environment, not a fresh
   *operating system*. Name one class of bug that a Windows-only fresh-venv test structurally cannot
   catch, that a real clean-OS test (a VM, a fresh WSL instance, a different machine entirely) could.

### Teach-back

> **"'It works on my machine' is true and useless at the same time — the interesting question is always *which* machine, and what it already has that yours doesn't."**
Explain why both real gaps M28 found (`make`, the Tesseract language pack) were things the owner
already knew how to work around without ever writing them down — and why that makes them *more*
dangerous to a new user, not less, despite (or because of) being invisible in the owner's own daily
use of the project.
