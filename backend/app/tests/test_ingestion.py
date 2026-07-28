import io

import pytest
from PIL import Image, ImageDraw

from app.services.ingestion import (
    CorruptDocumentError,
    DocumentTooManyPagesError,
    UnsupportedDocumentError,
    rasterize,
)


def _page(text: str) -> Image.Image:
    img = Image.new("RGB", (600, 400), "white")
    ImageDraw.Draw(img).text((40, 40), text, fill="black")
    return img


def _pdf_bytes(*texts: str) -> bytes:
    pages = [_page(t) for t in texts]
    buffer = io.BytesIO()
    pages[0].save(buffer, format="PDF", save_all=True, append_images=pages[1:])
    return buffer.getvalue()


def _png_bytes(text: str = "hello") -> bytes:
    buffer = io.BytesIO()
    _page(text).save(buffer, format="PNG")
    return buffer.getvalue()


def test_rasterize_multipage_pdf_returns_one_image_per_page() -> None:
    images = rasterize(
        _pdf_bytes("page one", "page two", "page three"),
        "application/pdf",
        max_pages=20,
        render_scale=2.0,
    )
    assert len(images) == 3
    # scale 2.0 over the 600x400 source page
    assert images[0].size == (1200, 800)
    assert all(img.mode == "RGB" for img in images)


def test_rasterize_png_returns_single_image() -> None:
    images = rasterize(_png_bytes(), "image/png", max_pages=20, render_scale=3.0)
    assert len(images) == 1
    assert images[0].mode == "RGB"


def test_unsupported_content_type_raises() -> None:
    with pytest.raises(UnsupportedDocumentError):
        rasterize(b"whatever", "text/plain", max_pages=20, render_scale=3.0)


def test_corrupt_pdf_raises() -> None:
    with pytest.raises(CorruptDocumentError):
        rasterize(b"%PDF-not-really", "application/pdf", max_pages=20, render_scale=3.0)


def test_corrupt_image_raises() -> None:
    with pytest.raises(CorruptDocumentError):
        rasterize(b"not-an-image", "image/png", max_pages=20, render_scale=3.0)


def test_pdf_exceeding_page_limit_raises() -> None:
    with pytest.raises(DocumentTooManyPagesError):
        rasterize(_pdf_bytes("a", "b", "c"), "application/pdf", max_pages=2, render_scale=2.0)
