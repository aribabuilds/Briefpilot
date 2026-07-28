import pytesseract
from PIL.Image import Image

from app.schemas.ocr import BBox, OcrPage, OcrWord
from app.services.ocr.base import OcrService

# German + English: BriefPilot's letters are German, but addresses, product
# names, and the occasional English term appear. Requires the tesseract-ocr-deu
# language pack (installed in the Docker image and CI).
DEFAULT_LANGUAGE = "deu+eng"


class TesseractOcrService(OcrService):
    def __init__(self, language: str = DEFAULT_LANGUAGE, timeout: float = 0.0) -> None:
        self._language = language
        # Seconds before a single-page OCR call is abandoned; 0 disables the
        # timeout (pytesseract's convention). Guards against a pathological page
        # hanging a worker thread.
        self._timeout = timeout

    def extract_page(self, image: Image, page: int) -> OcrPage:
        data = pytesseract.image_to_data(
            image,
            lang=self._language,
            output_type=pytesseract.Output.DICT,
            timeout=self._timeout,
        )
        words = _normalize(data, image_width=image.width, image_height=image.height, page=page)
        return OcrPage(page=page, width=image.width, height=image.height, words=words)


def _normalize(
    data: dict[str, list[object]],
    *,
    image_width: int,
    image_height: int,
    page: int,
) -> list[OcrWord]:
    """Convert Tesseract's TSV-style dict into normalized OcrWords.

    Pure and provider-shaped so it is unit-testable without the Tesseract
    binary (the binary is only exercised by the CI integration test). Tesseract
    emits a row per layout element at every level; non-word rows carry conf -1
    and empty text, which are dropped here. Pixel geometry is converted to page
    fractions and confidence from 0-100 to [0, 1] — the schema's frozen shape.
    """
    words: list[OcrWord] = []
    for i in range(len(data["text"])):
        text = str(data["text"][i]).strip()
        confidence = float(str(data["conf"][i]))
        if not text or confidence < 0:
            continue

        left = float(str(data["left"][i]))
        top = float(str(data["top"][i]))
        width = float(str(data["width"][i]))
        height = float(str(data["height"][i]))

        words.append(
            OcrWord(
                text=text,
                page=page,
                bbox=BBox(
                    x=left / image_width,
                    y=top / image_height,
                    width=width / image_width,
                    height=height / image_height,
                ),
                confidence=confidence / 100.0,
            )
        )
    return words
