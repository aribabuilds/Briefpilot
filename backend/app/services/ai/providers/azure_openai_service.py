from openai import AsyncAzureOpenAI

from app.schemas.ai import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
    SummarizationRequest,
    SummarizationResult,
)
from app.services.ai.base import AIService

_DEFAULT_EXTRACTION_INSTRUCTIONS = "Extract structured data from the document."
_SUMMARIZATION_INSTRUCTIONS = "Summarize the following text."


class AzureOpenAIService(AIService):
    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self._deployment = deployment

    async def extract_document(
        self, request: DocumentExtractionRequest
    ) -> DocumentExtractionResult:
        response = await self._client.chat.completions.create(
            model=self._deployment,
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
            model=self._deployment,
            messages=[
                {"role": "system", "content": _SUMMARIZATION_INSTRUCTIONS},
                {"role": "user", "content": request.content},
            ],
            max_tokens=request.max_length,
        )
        summary = response.choices[0].message.content or ""
        return SummarizationResult(summary=summary)
