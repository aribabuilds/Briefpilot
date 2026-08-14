# LinkedIn post #2 — draft (project close, M1–M29)

**Status:** draft only. Claude drafts; publishing is yours — edit freely, this is a starting point,
not a final copy. Same rule as post #1: concrete numbers, no hype.

---

I just closed out a 29-milestone portfolio project: BriefPilot, a tool that reads a photo of a
German bureaucratic letter and explains it in plain English — grounded, sourced, and honest about
what it doesn't know.

The feature list is the easy part to describe. The harder part — and the part I actually want to
talk about — is the anti-hallucination design underneath it, because that's the part that generalizes
past this one project.

**Every extracted field carries a confidence and a source location, not just a value.** Click any
field on the result page and it highlights the exact words in your original scan it came from. If it
can't find that link, it says so — "could not be matched, verify manually" — instead of pretending.

**Nothing is ever silently corrected.** A deadline before the letter date, a negative amount, an
unrecognized legal reference — all get flagged with a machine-readable code and a lowered confidence.
The value itself is never rewritten. The pipeline is allowed to be wrong; it's not allowed to hide it.

**The explanation is checked twice, not once.** The prompt says "never give advice." A separate,
deterministic linter then re-scans the model's *actual output* for advice-phrase patterns — because a
prompt instruction is a request, not a guarantee, and I didn't want to trust that it worked.

Three real numbers from building it:

- **245 backend tests, 0 flaky**, including a from-scratch dependency install in a genuinely fresh
  Python environment (not the one I'd been developing against) — same result, first try.
- **4 real bugs found in one session**, the first time I ran the pipeline against a real LLM API
  instead of test fixtures: two retired model names, a JSON-formatting quirk the docs don't mention,
  and a cached client that broke across event loops. None of it showed up in unit tests. Real
  third-party systems don't match their documentation as often as you'd hope.
- **$0 spent.** Self-hosted OCR (Tesseract), a free-tier LLM, no hosted deployment, no database
  beyond memory that auto-purges within 24 hours. The zero-cost constraint shaped real architecture
  decisions, not just the bill — it's the whole reason storage is in-memory-only, which turned out to
  be a *stronger* privacy guarantee than the 24-hour promise, not a weaker one.

The honest parts of the story matter as much as the shipped parts: the eval scorecard is fully built
and has scored zero real letters, because I refused to fabricate the golden set just to make a number
look good. That's still true today. It'll stay true until real letters exist to measure against —
and I'd rather say that plainly than round it up.

Repo, ADRs, and the full decisions log: [link]

#buildinpublic #softwareengineering #llm #promptengineering #ai
