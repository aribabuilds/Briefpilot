import asyncio
import contextlib
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.services.job_service import get_job_service

settings = get_settings()
configure_logging(settings)
logger = structlog.get_logger(__name__)


async def _retention_sweep_loop() -> None:
    """Runs for the app's lifetime, purging jobs/documents older than
    retention_max_age_hours every retention_sweep_interval_seconds (M22).
    A failed sweep is logged, not raised -- one bad sweep must not kill all
    future ones, the same best-effort posture JobService uses for its AI
    steps."""
    service = get_job_service()
    max_age = timedelta(hours=settings.retention_max_age_hours)
    while True:
        await asyncio.sleep(settings.retention_sweep_interval_seconds)
        try:
            purged = service.purge_expired(now=datetime.now(UTC), max_age=max_age)
            if purged:
                logger.info("retention_sweep_purged", count=len(purged))
        except Exception:  # noqa: BLE001 - a sweep failure must not stop the loop
            logger.exception("retention_sweep_failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_retention_sweep_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """M24: one structured log line per request (method, path, status,
    duration, client IP) -- the operational visibility layer CLAUDE.md §3
    calls for (structured logs, no paid APM). Deliberately logs the path and
    status only, never the request body: nothing here should ever carry the
    text of a user's letter (see docs/privacy page's "what leaves this
    server" claim -- this middleware has to actually honor it, not just
    every individual log call downstream)."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else None,
    )
    return response


app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running"}
