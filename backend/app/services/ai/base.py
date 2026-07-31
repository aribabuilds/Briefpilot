from abc import ABC, abstractmethod

from app.schemas.ai import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
    SummarizationRequest,
    SummarizationResult,
)
from app.schemas.classification import ClassificationRequest, ClassificationResult


class AIService(ABC):
    @abstractmethod
    async def extract_document(
        self, request: DocumentExtractionRequest
    ) -> DocumentExtractionResult: ...

    @abstractmethod
    async def summarize(self, request: SummarizationRequest) -> SummarizationResult: ...

    @abstractmethod
    async def classify_document(self, request: ClassificationRequest) -> ClassificationResult: ...
