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
