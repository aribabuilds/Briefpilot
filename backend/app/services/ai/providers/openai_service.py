from openai import AsyncOpenAI

from app.schemas.ai import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
    SummarizationRequest,
    SummarizationResult,
)
from app.services.ai.base import AIService

_DEFAULT_EXTRACTION_INSTRUCTIONS = "Extract structured data from the document."
_SUMMARIZATION_INSTRUCTIONS = "Summarize the following text."


class OpenAIService(AIService):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def extract_document(
        self, request: DocumentExtractionRequest
    ) -> DocumentExtractionResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": request.instructions or _DEFAULT_EXTRACTION_INSTRUCTIONS,
                },
                {"role": "user", "content": request.content},
            ],
        )
        raw_response = response.choices[0].message.content or ""
        return DocumentExtractionResult(extracted_data={}, raw_response=raw_response)

    async def summarize(self, request: SummarizationRequest) -> SummarizationResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SUMMARIZATION_INSTRUCTIONS},
                {"role": "user", "content": request.content},
            ],
            max_tokens=request.max_length,
        )
        summary = response.choices[0].message.content or ""
        return SummarizationResult(summary=summary)
