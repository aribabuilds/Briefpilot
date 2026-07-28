import io

import pytest
from PIL import Image, ImageDraw
from PIL.Image import Image as PILImage

from app.schemas.ocr import BBox, OcrPage, OcrWord
from app.services.document_pipeline import DocumentOcrError, build_document
from app.services.ocr.base import OcrService


def _pdf_bytes(pages: int) -> bytes:
    images = []
    for i in range(pages):
        img = Image.new("RGB", (600, 400), "white")
        ImageDraw.Draw(img).text((40, 40), f"page {i}", fill="black")
        images.append(img)
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


class _FakeOcr(OcrService):
    """Returns one deterministic word per page; records the pages it was asked for."""

    def __init__(self) -> None:
        self.seen: list[int] = []

    def extract_page(self, image: PILImage, page: int) -> OcrPage:
        self.seen.append(page)
        word = OcrWord(
            text=f"word{page}",
            page=page,
            bbox=BBox(x=0.1, y=0.1, width=0.2, height=0.1),
            confidence=0.9,
        )
        return OcrPage(page=page, width=image.width, height=image.height, words=[word])


class _FlakyOcr(OcrService):
    """Always fails on ``fail_page``; succeeds elsewhere."""

    def __init__(self, fail_page: int) -> None:
        self._fail_page = fail_page

    def extract_page(self, image: PILImage, page: int) -> OcrPage:
        if page == self._fail_page:
            raise RuntimeError("simulated OCR failure")
        word = OcrWord(
            text=f"word{page}",
            page=page,
            bbox=BBox(x=0.1, y=0.1, width=0.2, height=0.1),
            confidence=0.9,
        )
        return OcrPage(page=page, width=image.width, height=image.height, words=[word])


def _kwargs() -> dict[str, object]:
    return {
        "max_pages": 20,
        "render_scale": 2.0,
        "preprocess_enabled": True,
        "deskew_max_angle": 15.0,
        "max_dimension": 3000,
    }


def test_build_document_produces_one_page_per_source_page() -> None:
    ocr = _FakeOcr()
    document = build_document(_pdf_bytes(3), "application/pdf", ocr=ocr, **_kwargs())  # type: ignore[arg-type]

    assert [page.page for page in document.pages] == [0, 1, 2]
    assert ocr.seen == [0, 1, 2]
    assert document.text.split() == ["word0", "word1", "word2"]


def test_build_document_isolates_a_failing_page() -> None:
    document = build_document(
        _pdf_bytes(3),
        "application/pdf",
        ocr=_FlakyOcr(fail_page=1),
        max_attempts=2,
        **_kwargs(),  # type: ignore[arg-type]
    )

    # Document stays intact and correctly paginated; the bad page is just empty.
    assert len(document.pages) == 3
    assert document.pages[1].words == []
    assert document.pages[0].words and document.pages[2].words


def test_build_document_raises_when_every_page_fails() -> None:
    # A dead engine (every page raises) is a systemic failure, surfaced — not a
    # silently-empty "success". Guards against the D2 silent-failure trap.
    class _DeadOcr(OcrService):
        def __init__(self) -> None:
            self.attempts = 0

        def extract_page(self, image: PILImage, page: int) -> OcrPage:
            self.attempts += 1
            raise RuntimeError("always fails")

    ocr = _DeadOcr()
    with pytest.raises(DocumentOcrError):
        build_document(
            _pdf_bytes(2), "application/pdf", ocr=ocr, max_attempts=3, **_kwargs()  # type: ignore[arg-type]
        )
    assert ocr.attempts == 6  # 2 pages x 3 attempts each


def test_build_document_keeps_a_blank_page_as_success() -> None:
    # A page that returns zero words WITHOUT raising is blank, not failed, so the
    # document completes normally rather than being treated as a total failure.
    class _BlankOcr(OcrService):
        def extract_page(self, image: PILImage, page: int) -> OcrPage:
            return OcrPage(page=page, width=image.width, height=image.height, words=[])

    document = build_document(
        _pdf_bytes(1), "application/pdf", ocr=_BlankOcr(), **_kwargs()  # type: ignore[arg-type]
    )
    assert len(document.pages) == 1
    assert document.pages[0].words == []
