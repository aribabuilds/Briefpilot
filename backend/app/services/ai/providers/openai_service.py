from openai import AsyncOpenAI

from app.schemas.ai import DocumentExtractionRequest, SummarizationRequest, SummarizationResult
from app.schemas.classification import ClassificationRequest, ClassificationResult
from app.schemas.extraction import LetterExtraction
from app.services.ai.base import AIService
from app.services.ai.classification_parsing import parse_classification_response
from app.services.ai.extraction_parsing import parse_letter_extraction
from app.services.ai.prompts.classify import (
    CLASSIFICATION_SYSTEM_INSTRUCTION,
    build_classification_user_message,
)
from app.services.ai.prompts.extract import (
    EXTRACTION_SYSTEM_INSTRUCTION,
    build_extraction_user_message,
)

_SUMMARIZATION_INSTRUCTIONS = "Summarize the following text."


class OpenAIService(AIService):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def extract_document(self, request: DocumentExtractionRequest) -> LetterExtraction:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_INSTRUCTION},
                {"role": "user", "content": build_extraction_user_message(request.content)},
            ],
        )
        return parse_letter_extraction(response.choices[0].message.content or "")

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

    async def classify_document(self, request: ClassificationRequest) -> ClassificationResult:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_INSTRUCTION},
                {"role": "user", "content": build_classification_user_message(request.content)},
            ],
        )
        return parse_classification_response(response.choices[0].message.content or "")
