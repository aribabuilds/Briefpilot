# ADR-0008 — Document viewer serves raw rasterized pages, not OCR-preprocessed ones

- **Status:** Accepted
- **Milestone:** M18
- **Date:** 2026-08-14

## Context

M18's story is "see the original scan of my letter." Until now, the raw uploaded bytes were never
persisted anywhere past the request that received them: `create_job` passed `content: bytes`
straight into the OCR pipeline and the bytes were discarded once that call returned — there was
nothing to render even if a viewer existed.

Meanwhile, `services/preprocess.py` (M4) already transforms every page before OCR ever sees it:
grayscale → deskew → contrast enhancement → downscale. That pipeline exists to make OCR more
accurate, not to produce something meant for human eyes — but it's also the image `OcrDocument`'s
word-level `BBox` fractions (ADR-0002) are actually computed against. Displaying a *different* image
than the one those fractions describe risks a future overlay (M19) drawing boxes that don't
visually line up with the letter's real content, if the deskew step rotated anything non-trivially.

## Decision

**Persist the raw upload bytes** (`repositories/document_store.py`: `DocumentStore` ABC +
`InMemoryDocumentStore`, mirroring `JobRepository`'s own shape) and **serve the RAW, un-preprocessed
rasterization** — `services/ingestion.rasterize()`, the exact function already used as OCR's own
first step, called again with no grayscale/deskew/contrast changes applied — through a new
`GET /jobs/{id}/pages/{n}` endpoint returning PNG bytes.

This matches M18's literal story: the user sees their actual photo or scan, in color, at its
original orientation — not a grayscale, rotated, contrast-boosted version optimized for a text
recognizer.

## Alternatives considered

**Serve the OCR-preprocessed image instead**, guaranteeing pixel-exact alignment with every `BBox`
computed against it. Rejected for M18 specifically: a grayscale, deskewed image is a materially
different, less recognizable object than "my letter" to the person who photographed it — CLAUDE.md's
own framing is trust ("prove the AI didn't invent it"), and showing someone a processed version of
their document undercuts that "this is really your letter" recognition the raw image provides.
Deferred, not dismissed: if M19 finds the alignment gap actually matters in practice (see "Revisit
when"), switching the served image is a one-line change to this endpoint, not a redesign.

**Push PDF rendering to the frontend** (a client-side PDF.js dependency) instead of reusing the
backend's existing `pypdfium2`-based rasterization. Rejected: this project already has a
zero-new-heavy-dependency posture (CLAUDE.md §3, ADR-0001), and the backend already rasterizes every
PDF page for OCR — reusing that exact function for display avoids a second rendering pipeline (and a
second source of "did this render the same way OCR saw it" uncertainty) for zero added dependency
cost.

## Consequences

- **Raw upload bytes now live for the process's lifetime**, not just for the duration of one
  request. This is new: nothing about the upload survived past OCR before M18. `DocumentStore` is
  deliberately a separate boundary from `JobRepository` (not bolted onto the `Job`/`JobResult` JSON
  schema, which would bloat every poll response with a blob) — the same separation-of-concerns
  reasoning that kept `SourceSpan`'s `BBox`es embedded directly in `ExtractedField` (ADR-0004)
  rather than requiring a second lookup.
- **A real privacy surface now exists that didn't before M18**: uploaded document bytes persist
  in-memory for as long as the process runs, with no expiry. M22 ("one-click delete... 24h
  auto-purge") is the milestone that has to actually close this gap; it is explicitly not closed by
  M18, and `PROGRESS.md`'s Known Deviations table names it so it isn't forgotten.
- **The deskew-alignment question is now open, on the record, for M19 to resolve** — not silently
  assumed away. M19's "tap a field, see it highlighted" interaction is the first place pixel-exact
  alignment between a `BBox` and the *displayed* image actually matters; M18 only had to prove the
  display and the coordinate math work, not that they're reconciled with each other.

## Revisit when

- M19 is designed: either the raw-image choice holds (most real photos aren't rotated enough for
  deskew to move box positions visibly), or M19 needs to switch the served image, store the deskew
  angle so the frontend can counter-rotate boxes, or overlay against the preprocessed image instead
  — a decision with real evidence (how much do real photos actually get deskewed?) instead of a
  guess made now with zero golden letters to check it against.
- M22's retention design lands, at which point `DocumentStore`'s in-memory-forever behavior needs a
  real expiry/deletion story, not just an interface that could support one.
