from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # NoDecode: pydantic-settings otherwise tries to JSON-decode any list-typed
    # env value before our validator below ever runs, which rejects a plain
    # comma-separated string like ".env"'s CORS_ORIGINS=http://localhost:3000.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
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

    # Quality gate (M6): a document that reads with fewer words than
    # min_word_count, or a mean word confidence below min_mean_confidence, is
    # marked LOW_QUALITY and the user is asked to retake. Tune against real photos.
    min_mean_confidence: float = 0.5
    min_word_count: int = 5

    # Preprocessing (M4). Deskew only corrects within +/- this angle; beyond it
    # the estimate is treated as unreliable and skipped. Downscale bounds the
    # longest side to cap OCR cost on large phone photos.
    preprocess_enabled: bool = True
    deskew_max_angle: float = 15.0
    preprocess_max_dimension: int = 3000

    # Retention / auto-purge (M22). No accounts means there's no user action
    # that reliably signals "I'm done with this" other than the explicit
    # delete button, so everything also expires on a timer regardless --
    # CLAUDE.md §5.6 requires the privacy page's claims to match what the
    # code actually does, not just what it says. The sweep interval is a
    # separate knob from the retention window itself: it only controls how
    # promptly an expired job actually gets swept, not how long data lives.
    retention_max_age_hours: float = 24.0
    retention_sweep_interval_seconds: float = 3600.0

    # Rate limiting (M24): a lightweight in-memory sliding-window limiter,
    # keyed by client IP, guards the two state-changing endpoints (upload,
    # delete) against abusive traffic. No Redis -- consistent with the
    # in-memory job/document stores this app already runs on (ADR-0001).
    # 20/min comfortably covers a real user re-uploading a few misread
    # photos in a row while still bounding a scripted flood.
    rate_limit_max_requests: int = 20
    rate_limit_window_seconds: float = 60.0

    # Default is the free-tier provider (CLAUDE.md §3: no paid API calls by
    # default). OpenAI/Azure remain available as an explicit opt-in — see
    # docs/adr/0003-free-tier-llm-default-and-aiservice-naming.md.
    ai_provider: Literal["gemini", "openai", "azure_openai"] = "gemini"
    gemini_api_key: str | None = None
    # 2.0-flash AND 2.5-flash were both retired by Google for new API keys
    # (confirmed via live 404s against this project's key, 2026-08-13) --
    # verified directly against the API that 3.5/3.6/3.7-flash all still work;
    # 3.5 is the most conservative (oldest, least likely to be preview/
    # unstable) of the three. Pinned to a specific version rather than
    # tracking the "gemini-flash-latest" alias so a future model swap is a
    # deliberate version bump here, not a silent behavior change from
    # Google's side -- this is the second time that distinction has mattered
    # in one debugging session.
    gemini_model: str = "gemini-3.5-flash"
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
