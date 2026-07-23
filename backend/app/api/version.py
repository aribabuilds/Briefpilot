from fastapi import APIRouter

from app.config.settings import get_settings
from app.schemas.version import VersionResponse

router = APIRouter(tags=["version"])


@router.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(name=settings.app_name, version=settings.app_version)
