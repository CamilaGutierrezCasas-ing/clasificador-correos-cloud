from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/info", tags=["Info"])
settings = get_settings()


@router.get("")
def app_info() -> dict:
    return {
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "api_prefix": settings.api_v1_str,
        "docs": "/docs",
        "version": "fase-1",
    }
