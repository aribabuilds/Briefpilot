from abc import ABC, abstractmethod

from PIL.Image import Image

from app.schemas.ocr import OcrPage


class OcrService(ABC):
    """Contract for turning a page image into normalized, positioned words.

    The rest of the pipeline depends only on this interface and the OcrPage
    schema — never on a specific OCR engine. Swapping Tesseract for a paid
    provider means adding one adapter here (the same dependency-inversion seam
    as the AI layer), with no change to ingestion, extraction, or the overlay.
    """

    @abstractmethod
    def extract_page(self, image: Image, page: int) -> OcrPage:
        """Run OCR on a single page image and return its normalized words."""
