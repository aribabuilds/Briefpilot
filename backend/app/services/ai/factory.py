from app.config.settings import Settings, get_settings
from app.services.ai.base import AIService
from app.services.ai.providers.azure_openai_service import AzureOpenAIService
from app.services.ai.providers.gemini_service import GeminiService
from app.services.ai.providers.openai_service import OpenAIService


def build_ai_service(settings: Settings) -> AIService:
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY must be set when AI_PROVIDER=gemini.")
        return GeminiService(api_key=settings.gemini_api_key, model=settings.gemini_model)

    if settings.ai_provider == "azure_openai":
        if not (
            settings.azure_openai_api_key
            and settings.azure_openai_endpoint
            and settings.azure_openai_deployment
        ):
            raise RuntimeError(
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT "
                "must be set when AI_PROVIDER=azure_openai."
            )
        return AzureOpenAIService(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY must be set when AI_PROVIDER=openai.")
    return OpenAIService(api_key=settings.openai_api_key, model=settings.openai_model)


def get_ai_service() -> AIService:
    # Deliberately NOT @lru_cache'd. Every provider's async client (GeminiService,
    # OpenAIService, AzureOpenAIService) wraps an httpx.AsyncClient whose
    # connections get bound to whichever asyncio event loop was active when they
    # were opened. JobService's _classify/_extract each call asyncio.run() --
    # creating and closing a fresh event loop per call -- so a *cached*,
    # shared client would hand its second caller connections still tied to a
    # now-closed loop, raising "RuntimeError: Event loop is closed" during
    # connection cleanup. A fresh AIService (and thus a fresh client) per call
    # scopes those connections to that call's own loop and nothing else.
    # Construction itself makes no network call, so this costs an object
    # allocation per job, not a real request.
    return build_ai_service(get_settings())
