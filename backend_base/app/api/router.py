from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.emails import router as emails_router
from app.api.health import router as health_router
from app.api.info import router as info_router
from app.api.microsoft import router as microsoft_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(info_router)
api_router.include_router(auth_router)
api_router.include_router(emails_router)
api_router.include_router(microsoft_router)
api_router.include_router(admin_router)