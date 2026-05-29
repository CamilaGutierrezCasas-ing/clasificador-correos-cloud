from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.ml.classifier import ensure_model_artifacts
from app.services.seed_service import seed_default_admin, seed_roles

from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_root():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_app(full_path: str):
        if (
            full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("openapi.json")
            or full_path.startswith("redoc")
        ):
            raise HTTPException(status_code=404, detail="Not found")

        requested_file = STATIC_DIR / full_path

        if requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(STATIC_DIR / "index.html")