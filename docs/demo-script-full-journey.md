# Full-journey demo script (M27)

Supersedes `docs/demo-script-sprint1.md` for recording purposes — that one only proved "OCR
exists" at the end of Sprint 1. This covers the whole shipped journey (M1–M24): upload → OCR →
classify → extract → validate → explain → highlight → delete. Still a script for *you* to record;
no screen-recording tool is available here, and a demo video shouldn't be synthesized from
screenshots pretending to be continuous footage.

**Suggested tool:** Windows: `Win+Alt+R` (Xbox Game Bar) or OBS Studio — both free, self-hosted.

## Setup before recording

1. Backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`) both running natively —
   see the README's "Quick start (native)."
2. A real `GEMINI_API_KEY` set, so classification/extraction/explanation actually populate (without
   one, the demo still works but those three fields stay `null` — fine as a fallback take, weaker as
   the main one).
3. Have one clean, real (or the `docs/finanzamt_testbrief.pdf` synthetic fixture — explicitly
   fictional, safe to use on camera) letter ready. Optionally a second, deliberately blurry photo for
   the quality-gate beat.
4. Fresh browser tab at the landing page, no other tabs/notifications visible.

## Shot list (~3 minutes)

| Time | Shot | What it proves |
|---|---|---|
| 0:00–0:10 | Landing page: tagline, "no account, auto-deleted within 24h" footer link visible | Product framing + the privacy promise up front, not buried |
| 0:10–0:20 | Select and upload a real letter (camera or file picker) | Real upload, not a canned demo |
| 0:20–0:30 | "Reading your letter…" processing state | The async job→poll contract actually running, not instant/faked |
| 0:30–0:45 | Results land: summary card (sender/deadline/amount at a glance), doc-type badge with confidence | Classification + extraction landed, with an honest confidence number attached |
| 0:45–1:05 | Scroll to the plain-English explanation + disclaimer | Grounded, ≤200-word, "explains — never advises" |
| 1:05–1:25 | Scroll to the action checklist; point out an urgent-flagged item if the letter has a near deadline | Deadline-sorted, urgency-aware, derived with zero extra AI calls |
| 1:25–1:35 | Tap a glossary term (an Amtsdeutsch word) → inline definition appears | The 58-term glossary, no page navigation |
| 1:35–2:00 | Click an extracted field (e.g. "Sender") → the original scan scrolls into view and the exact bounding box pulses | **The signature feature**: click-to-highlight, proving the AI didn't invent the value |
| 2:00–2:10 | Click a field with no `source_span` (if the letter has one) → the "could not be matched, verify manually" prompt | Honest about what it *can't* verify, not just what it can |
| 2:10–2:30 | Click "Delete my document" → confirm → "Deleted. This document and everything extracted from it are gone" | One-click delete, and the UI proves it (re-fetches and checks 404) rather than just claiming success |
| 2:30–2:45 | Click through to `/privacy` briefly | The privacy page matches what was just demonstrated, not a generic policy |
| 2:45–3:00 | (Optional) Upload the deliberately blurry photo → `RetakePrompt`, no garbled text shown | The quality gate still holding, even this late in the pipeline |

## What NOT to worry about

- Real Gemini free-tier quota is ~20 requests/day — do one real take, not a dozen rehearsals against
  the live API. Rehearse the clicks/scrolling against a `low_quality`/no-key fallback run first if
  you want to practice timing without spending quota.
- Narration is optional; the on-screen states are legible without it, but a few spoken sentences on
  "why this field is unverified" or "why nothing is stored past 24h" land well for a hiring-manager
  audience.
- Don't chase pixel-perfect OCR accuracy in the take you record — the eval scorecard (M12/M25, once
  unblocked) is what actually claims accuracy; this video's job is showing the *journey*, not proving
  a number.

## After recording

- Save under `docs/demo/` — a `.webm`/`.mp4` is a large binary; keep it out of git (add the folder to
  `.gitignore` if you commit anything alongside it) and host it externally (YouTube unlisted, a Loom
  link, or attached directly to the portfolio README as a link) rather than in the repo itself.
- This is the raw material for the LinkedIn/portfolio post, not the post itself — same relationship
  `demo-script-sprint1.md` had to Sprint 1's post.
