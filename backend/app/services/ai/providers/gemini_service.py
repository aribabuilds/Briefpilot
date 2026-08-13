from google import genai
from google.genai.types import GenerateContentConfig

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


class GeminiService(AIService):
    """Google Gemini, via the free tier — the zero-cost default (CLAUDE.md §3).

    Uses the async client (`client.aio`); the sync client's generate_content is
    not a coroutine and would block the event loop.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def extract_document(self, request: DocumentExtractionRequest) -> LetterExtraction:
        config = GenerateContentConfig(
            system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=build_extraction_user_message(request.content),
            config=config,
        )
        return parse_letter_extraction(response.text or "")

    async def explain_document(
        self, request: DocumentExplanationRequest
    ) -> DocumentExplanationResult:
        config = GenerateContentConfig(
            system_instruction=EXPLANATION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=build_explanation_user_message(request.content, request.extraction),
            config=config,
        )
        return parse_explanation_response(response.text or "")

    async def classify_document(self, request: ClassificationRequest) -> ClassificationResult:
        config = GenerateContentConfig(
            system_instruction=CLASSIFICATION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=build_classification_user_message(request.content),
            config=config,
        )
        return parse_classification_response(response.text or "")
