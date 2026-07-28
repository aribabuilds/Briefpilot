"""Document intake: raw upload bytes -> a list of page images, one per page.

This is the boundary between "a file arrived" and "OCR can read it". It owns
format handling (PDF vs image) and page splitting, and it raises typed errors
the API layer maps to HTTP status codes. It knows nothing about OCR.

PDF rasterization uses pypdfium2 — a self-contained wheel with no system
binary (unlike pdf2image/poppler), which keeps the project reproducible on a
clean machine per ADR-0001. See ADR-0002 for the full library rationale.
"""

import io

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError

PDF_CONTENT_TYPE = "application/pdf"
IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png"})


class IngestionError(Exception):
    """Base class for document intake failures."""


class UnsupportedDocumentError(IngestionError):
    """The content type is not one we can rasterize."""


class CorruptDocumentError(IngestionError):
    """The bytes could not be opened as the declared type."""


class DocumentTooManyPagesError(IngestionError):
    """The document exceeds the configured page limit."""


def rasterize(
    content: bytes,
    content_type: str,
    *,
    max_pages: int,
    render_scale: float,
) -> list[Image.Image]:
    """Return one RGB image per page.

    `render_scale` multiplies the PDF's 72-DPI base (scale 3.0 ~ 216 DPI), a
    balance between OCR accuracy and speed/size. Images are returned as a
    single-page list.
    """
    if content_type == PDF_CONTENT_TYPE:
        return _rasterize_pdf(content, max_pages=max_pages, render_scale=render_scale)
    if content_type in IMAGE_CONTENT_TYPES:
        return [_load_image(content)]
    raise UnsupportedDocumentError(content_type)


def _rasterize_pdf(
    content: bytes,
    *,
    max_pages: int,
    render_scale: float,
) -> list[Image.Image]:
    try:
        pdf = pdfium.PdfDocument(content)
    except pdfium.PdfiumError as exc:
        raise CorruptDocumentError("The PDF could not be opened.") from exc

    try:
        page_count = len(pdf)
        if page_count > max_pages:
            raise DocumentTooManyPagesError(
                f"Document has {page_count} pages; the limit is {max_pages}."
            )
        return [
            pdf[i].render(scale=render_scale).to_pil().convert("RGB") for i in range(page_count)
        ]
    finally:
        pdf.close()


def _load_image(content: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise CorruptDocumentError("The image could not be opened.") from exc
    return image.convert("RGB")
