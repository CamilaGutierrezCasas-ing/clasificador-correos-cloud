from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.ml.classifier import ensure_model_artifacts
from app.services.seed_service import seed_default_admin, seed_roles

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_model_artifacts()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_default_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="Backend fase 3 con auth, roles y clasificación básica de correos.",
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/", tags=["Root"])
def root() -> dict:
    return {
        "message": "Backend fase 3 corriendo con auth y clasificación de correos.",
        "docs": "/docs",
        "api_prefix": settings.api_v1_str,
    }
