from abc import ABC, abstractmethod

from app.schemas.ai import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
    SummarizationRequest,
    SummarizationResult,
)


class AIService(ABC):
    @abstractmethod
    async def extract_document(
        self, request: DocumentExtractionRequest
    ) -> DocumentExtractionResult: ...

    @abstractmethod
    async def summarize(self, request: SummarizationRequest) -> SummarizationResult: ...
