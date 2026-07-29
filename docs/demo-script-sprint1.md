# Sprint-1 demo — shot list (30 seconds, raw)

Per the execution plan's Day-7 output: a raw 30-second screen capture, not a
polished edit. This is a script for *you* to record, not something Claude can
produce — no screen-recording tool is available here.

**Suggested tool:** Windows: `Win+Alt+R` (Xbox Game Bar clip) or OBS Studio (free).
Both are free and self-hosted per the zero-cost mandate.

## Setup before recording

1. `make dev` (or the two dev-server commands) running.
2. Have one **clean, in-focus** letter photo/PDF ready (the happy path) and,
   optionally, one **deliberately blurry** photo ready (to show the quality gate).
3. Clear the browser to a fresh tab at the landing page.

## Shot list (~30s total)

| Time | Shot | What it proves |
|---|---|---|
| 0–5s | Landing page: "BriefPilot — AI Case Manager for German Bureaucracy," upload control visible | The product framing |
| 5–12s | Select and upload a real letter photo/PDF | Real upload, not a canned demo |
| 12–18s | Result page: "Reading your letter…" spinner, then the extracted text appears | The async job→poll contract (D5) actually completing |
| 18–24s | (Optional second take) Upload the deliberately blurry photo → `RetakePrompt` appears with tips, **no garbled text shown** | The quality gate (M6) working on a real bad photo, live |
| 24–30s | Back to the clean result; scroll to show the extracted text is the real letter's content | Closes the loop — the text is real, not a placeholder |

## What NOT to worry about

- Rough edges are fine — it's explicitly a "raw" capture, not produced.
- No audio narration needed for this first one.
- Don't wait for perfect OCR accuracy — Sprint 1's claim is "OCR pipeline
  exists and works," not "extraction is accurate" (that's Sprint 2's claim,
  backed by the M12 eval scorecard).

## After recording

- Save under e.g. `docs/demo/sprint-1-raw.mp4` (not committed if large — add
  to `.gitignore` or host externally; a 30s clip is small enough either way,
  your call).
- This clip is raw material for the LinkedIn post, not the post itself.
