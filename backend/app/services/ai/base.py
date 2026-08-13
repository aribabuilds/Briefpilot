from abc import ABC, abstractmethod

from app.schemas.ai import (
    DocumentExplanationRequest,
    DocumentExplanationResult,
    DocumentExtractionRequest,
)
from app.schemas.classification import ClassificationRequest, ClassificationResult
from app.schemas.extraction import LetterExtraction


class AIService(ABC):
    @abstractmethod
    async def extract_document(self, request: DocumentExtractionRequest) -> LetterExtraction: ...

    @abstractmethod
    async def explain_document(
        self, request: DocumentExplanationRequest
    ) -> DocumentExplanationResult: ...

    @abstractmethod
    async def classify_document(self, request: ClassificationRequest) -> ClassificationResult: ...
