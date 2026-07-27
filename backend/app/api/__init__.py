from fastapi import APIRouter

from app.api import health, jobs, version
from app.config.settings import get_settings

_settings = get_settings()

api_router = APIRouter()

# Operational endpoints stay at the root, unversioned — health checks and
# version probes are infrastructure concerns, not part of the public API surface.
api_router.include_router(health.router)
api_router.include_router(version.router)

# Business endpoints are versioned so the contract can evolve without breaking
# existing clients.
api_router.include_router(jobs.router, prefix=_settings.api_v1_prefix)
