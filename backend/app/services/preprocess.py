"""Image preprocessing to lift OCR accuracy on real-world phone photos.

Sits between ingestion and OCR (ingestion -> preprocess -> OCR). Every step is
a pure ``Image -> Image`` transform so it can be unit-tested in isolation; the
*measured* accuracy lift is a CI-gated integration test (it needs the Tesseract
binary), mirroring the OCR adapter.

Preprocessing is deliberately conservative. Aggressive operations (e.g. hard
binarization) can *degrade* a clean digital-PDF render, so the default pipeline
is grayscale -> deskew -> local-contrast -> bounded downscale, and deskew only
corrects an angle it is confident about.

Coordinates are unaffected: preprocessing runs before OCR, so OCR reads the
corrected image and emits boxes against it. The ADR-0002 schema (page
fractions) also means a downscale cannot invalidate any stored coordinate.
"""

import cv2
import numpy as np
from PIL import Image

_GRAYSCALE_MODE = "L"


def to_grayscale(image: Image.Image) -> Image.Image:
    if image.mode == _GRAYSCALE_MODE:
        return image
    return image.convert(_GRAYSCALE_MODE)


def estimate_skew_angle(image: Image.Image, *, limit: float = 15.0, step: float = 0.5) -> float:
    """Estimate document skew in degrees via projection-profile maximization.

    For each candidate angle the image is rotated and the vertical projection
    (row sums) is taken; text lines align at the true angle, which maximizes the
    variance between adjacent rows. Robust for text pages, unlike ``minAreaRect``
    on a raw point cloud, whose angle is ambiguous for wide text blocks.
    """
    gray = _to_cv_gray(image)
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    candidates = np.arange(-limit, limit + step, step)
    scores = [_projection_score(binary, float(angle)) for angle in candidates]
    return float(candidates[int(np.argmax(scores))])


def deskew(image: Image.Image, *, max_angle: float = 15.0, min_angle: float = 0.5) -> Image.Image:
    """Straighten the page if a confident, non-trivial skew is detected.

    Skips (returns the input unchanged) when the estimate is below ``min_angle``
    (nothing worth resampling for) or saturates near the search boundary (the
    true skew is outside the window, so the estimate is unreliable — never
    rotate on a guess, and never half-correct a badly rotated page).
    """
    angle = estimate_skew_angle(image, limit=max_angle)
    saturated = abs(angle) > max_angle - 1.0
    if abs(angle) < min_angle or saturated:
        return image
    return _rotate(image, angle)


def enhance_contrast(image: Image.Image) -> Image.Image:
    """Local (adaptive) contrast via CLAHE — recovers unevenly lit photos."""
    gray = _to_cv_gray(image)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return Image.fromarray(clahe.apply(gray))  # 2D uint8 -> mode "L"


def downscale(image: Image.Image, *, max_dimension: int) -> Image.Image:
    """Bound the longest side to ``max_dimension`` (never upscales)."""
    longest = max(image.size)
    if longest <= max_dimension:
        return image
    ratio = max_dimension / longest
    new_size = (round(image.width * ratio), round(image.height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def preprocess_page(
    image: Image.Image,
    *,
    enabled: bool = True,
    deskew_max_angle: float = 15.0,
    max_dimension: int = 3000,
) -> Image.Image:
    """Run the default pipeline: grayscale -> deskew -> contrast -> downscale."""
    if not enabled:
        return image
    result = to_grayscale(image)
    result = deskew(result, max_angle=deskew_max_angle)
    result = enhance_contrast(result)
    result = downscale(result, max_dimension=max_dimension)
    return result


# --- OpenCV bridge helpers -------------------------------------------------


def _to_cv_gray(image: Image.Image) -> np.ndarray:
    array = np.array(image)
    if array.ndim == 2:
        return array
    return cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)


def _projection_score(binary: np.ndarray, angle: float) -> float:
    rotated = _warp(binary, angle, border_value=0)
    projection = rotated.sum(axis=1, dtype=np.float64)
    deltas = np.diff(projection)
    return float(np.square(deltas).sum())


def _rotate(image: Image.Image, angle: float) -> Image.Image:
    array = np.array(image)
    # White border matches the (grayscale) page background so corners don't
    # introduce dark artifacts that OCR would try to read.
    rotated = _warp(array, angle, border_value=255)
    return Image.fromarray(rotated)  # infers mode from array shape


def _warp(array: np.ndarray, angle: float, *, border_value: int) -> np.ndarray:
    height, width = array.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        array,
        matrix,
        (width, height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )
