from app.services.ocr.tesseract_service import _normalize

# A Tesseract image_to_data(DICT) sample on a 1000x500 page: two real words and
# two structural rows (conf -1, empty text) that must be dropped.
SAMPLE: dict[str, list[object]] = {
    "text": ["", "Finanzamt", "", "München"],
    "conf": [-1, 96, -1, 88],
    "left": [0, 100, 0, 300],
    "top": [0, 50, 0, 50],
    "width": [1000, 150, 1000, 120],
    "height": [500, 40, 500, 40],
}


def test_normalize_drops_non_word_rows() -> None:
    words = _normalize(SAMPLE, image_width=1000, image_height=500, page=0)
    assert [w.text for w in words] == ["Finanzamt", "München"]


def test_normalize_converts_pixels_to_page_fractions() -> None:
    words = _normalize(SAMPLE, image_width=1000, image_height=500, page=0)
    first = words[0]
    assert first.bbox.x == 100 / 1000
    assert first.bbox.y == 50 / 500
    assert first.bbox.width == 150 / 1000
    assert first.bbox.height == 40 / 500


def test_normalize_scales_confidence_to_unit_interval() -> None:
    words = _normalize(SAMPLE, image_width=1000, image_height=500, page=0)
    assert words[0].confidence == 0.96
    assert words[1].confidence == 0.88


def test_normalize_stamps_page_index() -> None:
    words = _normalize(SAMPLE, image_width=1000, image_height=500, page=4)
    assert all(w.page == 4 for w in words)


def test_normalize_empty_input_returns_no_words() -> None:
    empty: dict[str, list[object]] = {
        "text": [],
        "conf": [],
        "left": [],
        "top": [],
        "width": [],
        "height": [],
    }
    assert _normalize(empty, image_width=100, image_height=100, page=0) == []
