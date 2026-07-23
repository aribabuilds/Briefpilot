import pytest

from app.config.settings import Settings
from app.services.ai.base import AIService
from app.services.ai.factory import build_ai_service
from app.services.ai.providers.azure_openai_service import AzureOpenAIService
from app.services.ai.providers.openai_service import OpenAIService


def _settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def test_ai_service_is_not_directly_instantiable() -> None:
    with pytest.raises(TypeError):
        AIService()  # type: ignore[abstract]


def test_openai_provider_conforms_to_interface() -> None:
    assert issubclass(OpenAIService, AIService)


def test_azure_openai_provider_conforms_to_interface() -> None:
    assert issubclass(AzureOpenAIService, AIService)


def test_factory_builds_openai_service_by_default() -> None:
    settings = _settings(ai_provider="openai", openai_api_key="test-key")
    service = build_ai_service(settings)
    assert isinstance(service, OpenAIService)
    assert isinstance(service, AIService)


def test_factory_builds_azure_openai_service_when_selected() -> None:
    settings = _settings(
        ai_provider="azure_openai",
        azure_openai_api_key="test-key",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_deployment="briefpilot-gpt",
    )
    service = build_ai_service(settings)
    assert isinstance(service, AzureOpenAIService)
    assert isinstance(service, AIService)


def test_factory_raises_when_openai_key_missing() -> None:
    settings = _settings(ai_provider="openai", openai_api_key=None)
    with pytest.raises(RuntimeError):
        build_ai_service(settings)


def test_factory_raises_when_azure_config_incomplete() -> None:
    settings = _settings(ai_provider="azure_openai", azure_openai_api_key="test-key")
    with pytest.raises(RuntimeError):
        build_ai_service(settings)
