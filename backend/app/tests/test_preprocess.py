import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.preprocess import (
    deskew,
    downscale,
    enhance_contrast,
    estimate_skew_angle,
    preprocess_page,
    to_grayscale,
)


def _text_page() -> Image.Image:
    image = Image.new("RGB", (800, 300), "white")
    font = ImageFont.load_default(size=40)
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(["Finanzamt Muenchen", "Bescheid 2026", "Bitte zahlen Sie"]):
        draw.text((40, 30 + i * 70), line, fill="black", font=font)
    return image


def _rotated(page: Image.Image, angle: float) -> Image.Image:
    return page.rotate(angle, expand=True, fillcolor="white", resample=Image.Resampling.BICUBIC)


def test_to_grayscale_converts_mode() -> None:
    assert to_grayscale(_text_page()).mode == "L"


def test_to_grayscale_is_noop_when_already_gray() -> None:
    gray = _text_page().convert("L")
    assert to_grayscale(gray) is gray


@pytest.mark.parametrize("rotation", [5.0, -7.0, 12.0, -3.0])
def test_estimate_skew_angle_recovers_known_rotation(rotation: float) -> None:
    # A PIL rotation of +r skews the text by +r; the estimator returns the
    # correction, which should be about -r. Half-degree search step => 0.75 tol.
    estimate = estimate_skew_angle(_rotated(_text_page(), rotation))
    assert estimate == pytest.approx(-rotation, abs=0.75)


def test_deskew_skips_trivial_angle() -> None:
    straight = _text_page()
    # No meaningful skew -> returned unchanged (no needless resampling).
    assert deskew(straight) is straight


def test_deskew_skips_when_estimate_saturates_at_bound() -> None:
    skewed = _rotated(_text_page(), 8.0)
    # A tight +/-2 window cannot reach the true 8 deg skew, so the estimate pegs
    # the boundary and is treated as unreliable -> skip rather than half-correct.
    assert deskew(skewed, max_angle=2.0) is skewed


def test_deskew_straightens_within_bound() -> None:
    skewed = _rotated(_text_page(), 8.0)
    corrected = deskew(skewed)
    # After correction the residual skew should be near zero.
    assert estimate_skew_angle(corrected) == pytest.approx(0.0, abs=1.0)


def test_enhance_contrast_returns_grayscale() -> None:
    assert enhance_contrast(_text_page()).mode == "L"


def test_downscale_bounds_longest_side() -> None:
    big = Image.new("RGB", (6000, 3000), "white")
    result = downscale(big, max_dimension=3000)
    assert max(result.size) == 3000
    assert result.size == (3000, 1500)  # aspect ratio preserved


def test_downscale_never_upscales() -> None:
    small = Image.new("RGB", (800, 600), "white")
    assert downscale(small, max_dimension=3000) is small


def test_preprocess_page_disabled_is_passthrough() -> None:
    page = _text_page()
    assert preprocess_page(page, enabled=False) is page


def test_preprocess_page_pipeline_outputs_bounded_grayscale() -> None:
    page = _rotated(_text_page(), 6.0)
    result = preprocess_page(page, max_dimension=500)
    assert result.mode == "L"
    assert max(result.size) <= 500
