# ADR-0002 — OCR engine and the normalized coordinate schema

- **Status:** Accepted
- **Milestone:** M3
- **Date:** 2026-07-27

## Context

OCR is the foundation of BriefPilot: it feeds classification, extraction, and —
critically — the source-highlight overlay, which draws a box around the exact
words a field came from. That overlay and every eval fixture are built against
whatever coordinate shape OCR emits, so this schema is one of the four decisions
the execution plan flags as "must not change once fixtures exist." Two things
must be decided together and frozen now: the OCR engine, and the coordinate
schema it normalizes to.

## Decision

**Engine: Tesseract** (self-hosted, open-source), via `pytesseract`.
German + English language packs (`deu+eng`).

**PDF rasterization: pypdfium2** — a self-contained wheel that renders PDF pages
to images with no system binary.

**Schema (frozen):** defined in `backend/app/schemas/ocr.py` —
`BBox → OcrWord → OcrPage → OcrDocument`. Two normalization rules make it
provider- and resolution-independent:

- **Bounding boxes are page fractions in [0, 1]**, not pixels. Origin top-left.
- **Confidence is [0, 1]**, converted from Tesseract's native 0-100 at the
  adapter boundary.

The engine sits behind an `OcrService` interface (`services/ocr/base.py`); the
concrete `TesseractOcrService` is the only place that imports `pytesseract`.

## Alternatives considered

### OCR engine

- **Azure Document Intelligence / Google Vision.** Higher accuracy on noisy
  phone photos, and native word-level boxes. **Rejected:** both are paid,
  metered APIs. `CLAUDE.md` §3 is a hard zero-cost mandate and forbids
  provisioning them. This is the "bake-off" the plan described, resolved by the
  budget constraint rather than a benchmark — standing up paid endpoints purely
  to compare would itself violate §3. The `OcrService` seam means adopting one
  later is a new adapter, not a rewrite, if a benchmark ever justifies the cost.
- **EasyOCR / PaddleOCR.** Also free and self-hostable. **Rejected for now:**
  heavier (PyTorch), slower on CPU, and Tesseract's `image_to_data` gives exactly
  the word-level geometry the overlay needs. Revisitable behind the same interface
  if Tesseract accuracy proves insufficient on the golden set (M13 decision point).

### PDF rasterization library

- **pdf2image + poppler.** Common, but needs the poppler *system binary* — an
  install step outside pip that undermines "clone and run on a clean machine"
  (ADR-0001). **Rejected.**
- **PyMuPDF (fitz).** Excellent and self-contained, but **AGPL-licensed**. Fine
  for this public portfolio, but AGPL's network-copyleft is a real constraint for
  anyone who forks it into a proprietary product. **Rejected** to keep the
  dependency story clean.
- **pypdfium2 (chosen).** Self-contained wheel, permissive license
  (BSD-3/Apache), backed by Chromium's PDFium. No system binary, no license
  trap.

### Coordinate representation

- **Pixel coordinates + page dimensions.** Tesseract-native and intuitive, but
  couples every stored box to the raster DPI: preprocessing that downscales a
  page (M4), or rendering at a different size, invalidates the numbers.
  **Rejected** in favor of page fractions, which survive any rescale.

## Consequences

- **A system dependency enters the stack.** Tesseract must be present at runtime.
  Handled: installed in `backend/Dockerfile` (so `make dev` works) and in the CI
  backend job. It is *not* on the owner's Windows machine, which drives the
  testing split below.
- **Testing splits by what needs the binary.** Normalization (pixels→fractions,
  confidence scaling, dropping non-word rows) is a pure function, unit-tested
  against a synthetic Tesseract dict with no binary. The real engine is exercised
  by a CI-gated integration test (`test_ocr_tesseract_integration.py`), skipped
  where Tesseract is absent. **CI, not a laptop, is the source of truth for OCR.**
- **Accuracy is now our problem, not a vendor's.** Tesseract on poor phone photos
  is weaker than the paid APIs; preprocessing (M4) exists specifically to recover
  that gap, and the quality gate (M6) catches inputs it still can't read.
- **The schema is a contract.** Downstream milestones (overlay M18, eval M12)
  depend on the frozen shape; changing it is a breaking change requiring a new ADR.

## Revisit when

- Tesseract accuracy on the golden set falls short at the M13 decision point —
  reconsider EasyOCR/PaddleOCR (free) behind the same interface, or escalate the
  paid-provider trade-off to the owner per the §3 protocol (what was tried free,
  cheapest paid option, exact cost, quality sacrificed to stay free).
