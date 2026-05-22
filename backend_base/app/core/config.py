from functools import lru_cache
from typing import List
import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Clasificador Correos Microsoft"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_str: str = "/api/v1"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/email_classifier"
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    jwt_secret_key: str = "cambia_esta_clave_en_tu_env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    default_admin_name: str = "Administrador"
    default_admin_email: str = "admin@local.com"
    default_admin_password: str = "Admin123*"


    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_redirect_uri: str = "http://localhost:8000/api/v1/microsoft/callback"
    microsoft_scopes: str = "openid profile offline_access User.Read Mail.Read"

    # URL del callback del frontend después de conectar Microsoft.
    # En producción será algo como: https://tu-frontend.vercel.app/microsoft/callback
    frontend_callback_url: str = "http://127.0.0.1:3000/microsoft/callback"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []

        raw_value = value.strip()
        if raw_value.startswith("["):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        return [item.strip() for item in raw_value.split(",") if item.strip()]
    
    @property
    def microsoft_scope_list(self) -> list[str]:
        return [item.strip() for item in self.microsoft_scopes.split() if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
