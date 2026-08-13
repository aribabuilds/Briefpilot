from openai import AsyncAzureOpenAI

from app.schemas.ai import (
    DocumentExplanationRequest,
    DocumentExplanationResult,
    DocumentExtractionRequest,
)
from app.schemas.classification import ClassificationRequest, ClassificationResult
from app.schemas.extraction import LetterExtraction
from app.services.ai.base import AIService
from app.services.ai.classification_parsing import parse_classification_response
from app.services.ai.explanation_parsing import parse_explanation_response
from app.services.ai.extraction_parsing import parse_letter_extraction
from app.services.ai.prompts.classify import (
    CLASSIFICATION_SYSTEM_INSTRUCTION,
    build_classification_user_message,
)
from app.services.ai.prompts.explain import (
    EXPLANATION_SYSTEM_INSTRUCTION,
    build_explanation_user_message,
)
from app.services.ai.prompts.extract import (
    EXTRACTION_SYSTEM_INSTRUCTION,
    build_extraction_user_message,
)


class AzureOpenAIService(AIService):
    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self._deployment = deployment

    async def extract_document(self, request: DocumentExtractionRequest) -> LetterExtraction:
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_INSTRUCTION},
                {"role": "user", "content": build_extraction_user_message(request.content)},
            ],
        )
        return parse_letter_extraction(response.choices[0].message.content or "")

    async def explain_document(
        self, request: DocumentExplanationRequest
    ) -> DocumentExplanationResult:
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": EXPLANATION_SYSTEM_INSTRUCTION},
                {
                    "role": "user",
                    "content": build_explanation_user_message(request.content, request.extraction),
                },
            ],
        )
        return parse_explanation_response(response.choices[0].message.content or "")

    async def classify_document(self, request: ClassificationRequest) -> ClassificationResult:
        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_INSTRUCTION},
                {"role": "user", "content": build_classification_user_message(request.content)},
            ],
        )
        return parse_classification_response(response.choices[0].message.content or "")
