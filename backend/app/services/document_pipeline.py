"""The document pipeline: raw upload bytes -> a normalized OcrDocument.

Composes the three pieces built in M3-M4 — ingestion (rasterize), preprocessing,
and OCR — into the single step the job worker runs. It is deliberately a plain
function of an injected ``OcrService`` so it can be tested with a fake OCR engine
(rasterize and preprocess run for real; only the binary-dependent OCR is faked).

Resilience with a limit: OCR is retried per page, and a page that keeps failing
becomes an empty page rather than sinking the whole document — one unreadable
page in a ten-page letter should not lose the other nine. But if *every* page
fails, that is not one bad page, it is a systemic failure (a dead OCR engine, a
misconfigured language pack), and it is raised as ``DocumentOcrError`` so the
job fails visibly instead of silently returning an empty document. A page that
is simply blank returns zero words *without* raising, so it counts as success.
"""

import structlog
from PIL.Image import Image

from app.schemas.ocr import OcrDocument, OcrPage
from app.services.ingestion import rasterize
from app.services.ocr.base import OcrService
from app.services.preprocess import preprocess_page

logger = structlog.get_logger(__name__)


class DocumentOcrError(Exception):
    """OCR failed on every page — a systemic failure, not one bad page."""


def build_document(
    content: bytes,
    content_type: str,
    *,
    ocr: OcrService,
    max_pages: int,
    render_scale: float,
    preprocess_enabled: bool,
    deskew_max_angle: float,
    max_dimension: int,
    max_attempts: int = 2,
) -> OcrDocument:
    images = rasterize(content, content_type, max_pages=max_pages, render_scale=render_scale)

    pages: list[OcrPage] = []
    failures = 0
    for index, image in enumerate(images):
        prepped = preprocess_page(
            image,
            enabled=preprocess_enabled,
            deskew_max_angle=deskew_max_angle,
            max_dimension=max_dimension,
        )
        page, succeeded = _extract_with_retry(ocr, prepped, page=index, max_attempts=max_attempts)
        pages.append(page)
        if not succeeded:
            failures += 1

    if images and failures == len(images):
        raise DocumentOcrError(f"OCR failed on all {len(images)} page(s).")
    return OcrDocument(pages=pages)


def _extract_with_retry(
    ocr: OcrService, image: Image, *, page: int, max_attempts: int
) -> tuple[OcrPage, bool]:
    """Return (page, succeeded). On exhausted retries, an empty page with
    succeeded=False so the caller can tell a failed page from a blank one."""
    for attempt in range(1, max_attempts + 1):
        try:
            return ocr.extract_page(image, page), True
        except Exception:
            logger.warning("ocr_page_failed", page=page, attempt=attempt, max_attempts=max_attempts)
    return OcrPage(page=page, width=image.width, height=image.height, words=[]), False
