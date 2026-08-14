# Retrospective — BriefPilot M1–M29

Written at the close of the milestone plan, before Sprint-5 candidates get triaged. Not a highlight
reel — `LEARNING.md` already has 30 milestones of decisions, review questions, and honest failure
analysis; this pulls back to the handful of things worth remembering across the whole project, the
ones that would still matter on a different project entirely.

## What actually shipped

A working, tested, documented pipeline: upload → OCR (with word-level bounding boxes, self-hosted,
free) → classify → extract → validate → explain → click-to-highlight → delete, running on $0 of
infrastructure. 245 backend tests, 6 Playwright specs, 10 ADRs, a milestone-by-milestone decisions
log, an eval harness ready to score against real letters the moment they exist. See `PROGRESS.md` for
the literal checklist; this is about what building it actually taught.

## The engineering lessons that generalize

**Null-not-guess, applied at every layer, is cheap to state and expensive to actually hold to.**
It's one sentence in `CLAUDE.md`. Holding it required: a parser that never fills in a plausible value
(M9), a linker that caps confidence instead of zeroing it when a value can't be verified (M10), a
validator that flags instead of silently correcting (M11), a UI that shows "could not be matched,
verify manually" instead of a blank space (M19). Four different layers, one discipline, applied
consistently enough that by M22 it was showing up unprompted in a privacy-page decision ("in-memory
means gone on restart — say that plainly, don't round it up to sound better").

**A cached singleton with mutable state is the single most recurring bug class in this codebase.**
Three separate times: `get_job_service()`'s `@lru_cache` reused across event loops (a real production
bug, found via the first live Gemini test); a test file assigning `lambda: _service()` instead of a
closed-over instance (M10, then again independently in M18's test); and a rate limiter's
`@lru_cache`'d singleton accumulating hit history across the entire pytest session (M24). Once the
pattern was named after the first occurrence, the second and third were caught in minutes instead of
hours — the specific bug matters less than recognizing its shape on sight.

**Deterministic, output-side checks are worth more than well-crafted prompts.** Every LLM-facing
safeguard in this project — the advice-phrase linter, the § whitelist, the readability check, the
M24 prompt-injection delimiter — followed the same rule: a prompt instruction is a request, not a
guarantee, and the thing that actually holds is a plain Python check run on what the model *actually
returned*. `advice_linter.py` doesn't trust the explanation prompt's "never give advice" instruction
to have worked; it re-checks. That distinction is the difference between a demo that looks safe and
one that's actually been verified.

**Documentation that insists on being checkable against the code finds real bugs feature work
doesn't.** M23's privacy page and M26's README rewrite each surfaced a genuine gap — an unfixed
retired model name in one `.env.example`, and a Postgres dependency that had been dead code since M2
— neither of which any test, lint pass, or CI run had ever caught, because nothing exercised those
paths. A documentation pass that refuses to write a claim it can't point at a specific line of code
to verify is a form of testing, not just writing.

## What was genuinely hard

**Real-world API behavior doesn't match the docs.** The first live run with a real Gemini key
surfaced four bugs in one session: two retired model names (404s with no warning), unreliable
`response_mime_type="application/json"` (prose leaking before *and* after the JSON on separate real
calls), a cached async client breaking across event loops, and a test gap that would have burned real
quota. None of this showed up in unit tests against synthetic fixtures — it only showed up the moment
a real external system was actually called. Synthetic tests prove the code does what you told it to;
they can't prove the code survives contact with a system you don't control.

**Knowing when *not* to build something was harder than building.** The OCR provider "bake-off" the
original plan called for never happened — the zero-cost mandate made the decision before a comparison
could (ADR-0002). The eval scorecard has been "ready to run" since M12 and has run zero times against
real data, because fabricating golden letters to make it look busy would have produced a scorecard
that measured nothing. An uptime monitor was scoped out entirely at M24 because there was nothing
real to point it at. Each of these is a milestone that *could* have shipped *something* — the harder,
more honest call was shipping nothing and saying exactly why.

## What I'd do differently starting over

- **Push more often.** The single biggest process gap this project surfaced wasn't in the code — it
  was that 14 commits' worth of real feature work (M15 through M28) sat local-only, never touched
  GitHub Actions, and went unreviewed for far longer than intended under "full speed, review later."
  The authorization to move fast was reasonable; letting the gap between local and remote grow that
  large wasn't a deliberate trade-off, it was drift. A standing rule — push at least every 3-4
  milestones regardless of review cadence — would have kept CI honest the whole way instead of only
  at M29.
- **Name the "known deviation" the moment it happens, not when documentation finally forces it into
  the open.** The Postgres gap existed from M2; it was only found at M26, while writing a README that
  insisted on being accurate. A lighter-weight version of that same discipline — a running "does this
  still match CLAUDE.md's stack decisions?" check at the end of each milestone — would have caught it
  five sprints earlier, for less total effort than the eventual README audit cost.
- **Treat "blocked on real data" as a standing weekly nudge, not a milestone-shaped wall.** M12, M13,
  M21, and M25 all hit the same wall (real golden letters, real human testers) and each got the same
  correct-but-repeated answer: can't fabricate, moving on. That's the right call every time it came
  up — but four separate milestones re-explaining the same blocker is a sign the *collection* process
  itself (not the pipeline) was under-resourced relative to how much of the roadmap depended on it.

## What actually held up

The anti-hallucination spine (CLAUDE.md §5) held at every single milestone that touched it, without
exception, across 29 milestones and a live API integration that broke in four different ways. That's
the number worth remembering from this project, more than any test count: not that nothing broke —
plenty did — but that the parts explicitly designed never to lie never did.
