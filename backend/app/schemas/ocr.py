"""Normalized OCR contract — FROZEN as of ADR-0002.

Every OCR provider (Tesseract today; a paid provider later) is normalized to
these types. The source-highlight overlay (M18) and every eval fixture (M12)
are built against this shape, so it must not change once fixtures exist.

Two deliberate normalization choices, both defended in ADR-0002:

1. Bounding boxes are stored as fractions of the page in [0, 1], not pixels.
   This makes them independent of the raster resolution — preprocessing (M4)
   can downscale a page, or the frontend can render it at any size, without
   invalidating a single stored coordinate. The overlay multiplies by whatever
   display size it uses; nothing downstream needs the OCR DPI.

2. Confidence is normalized to [0, 1], not Tesseract's native 0-100. The
   internal schema is provider-agnostic; provider-specific ranges are converted
   at the adapter boundary.
"""

from pydantic import BaseModel


class BBox(BaseModel):
    # All values are fractions of the page in [0, 1], origin at the top-left.
    x: float
    y: float
    width: float
    height: float


class OcrWord(BaseModel):
    text: str
    page: int  # 0-based page index
    bbox: BBox
    confidence: float  # [0, 1]


class OcrPage(BaseModel):
    page: int  # 0-based page index
    width: int  # rasterized page width in pixels (metadata; coords are fractional)
    height: int  # rasterized page height in pixels
    words: list[OcrWord]


class OcrDocument(BaseModel):
    pages: list[OcrPage]

    @property
    def words(self) -> list[OcrWord]:
        """Flattened word stream across all pages, in reading order per page."""
        return [word for page in self.pages for word in page.words]

    @property
    def text(self) -> str:
        """Whitespace-joined text of every word, pages separated by blank lines."""
        return "\n\n".join(" ".join(word.text for word in page.words) for page in self.pages)
