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
