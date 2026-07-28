from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BriefPilot"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql://briefpilot:briefpilot@localhost:5432/briefpilot"

    # Upload guard. Basic bound for the walking skeleton; streaming abuse guards
    # are M24. 10 MiB comfortably covers a multi-page phone photo or scanned PDF.
    max_upload_bytes: int = 10 * 1024 * 1024

    # Walking-skeleton stub: how long a job reports "processing" before its
    # placeholder result is ready. Removed when the real pipeline lands.
    stub_processing_delay_seconds: float = 1.5

    # Document ingestion / OCR (M3).
    ocr_language: str = "deu+eng"
    # PDF render scale over the 72-DPI base; 3.0 ~ 216 DPI, a balance of OCR
    # accuracy against render time and image size.
    ocr_render_scale: float = 3.0
    # Page-count guard against a pathological upload; also bounds OCR cost.
    max_document_pages: int = 20
    # Per-page OCR timeout (seconds; 0 = none) and the size of the background
    # worker pool that runs the document pipeline off the request path (M5).
    ocr_timeout_seconds: float = 30.0
    ocr_worker_threads: int = 2

    # Preprocessing (M4). Deskew only corrects within +/- this angle; beyond it
    # the estimate is treated as unreliable and skipped. Downscale bounds the
    # longest side to cap OCR cost on large phone photos.
    preprocess_enabled: bool = True
    deskew_max_angle: float = 15.0
    preprocess_max_dimension: int = 3000

    ai_provider: Literal["openai", "azure_openai"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-08-01-preview"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
