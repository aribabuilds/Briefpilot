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

### Review questions & teach-back

M1 is not closed yet — the remaining scope is pre-commit hooks, `make dev`, `docs/adr/`, and a
first real backend boot. The three review questions and the teach-back prompt will be appended
when M1 meets its Definition of Done.
