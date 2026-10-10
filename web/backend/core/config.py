"""HexaVeil CMS settings — mirrors remnawave's WebSettings pattern."""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CmsSettings(BaseSettings):
    """CMS settings from .env — compatible with PHP env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    # App
    debug: bool = Field(default=False, alias="APP_DEBUG")
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")

    # Database (same .env keys as PHP)
    db_driver: str = Field(default="pgsql", alias="DB_DRIVER")
    db_host: str = Field(default="db", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="cms", alias="DB_NAME")
    db_user: str = Field(default="cms", alias="DB_USER")
    db_pass: str = Field(default="cms_secret_2026", alias="DB_PASS")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    # JWT — must match PHP JWTAuth.php exactly
    # PHP reads: JWT_SECRET → APP_ENCRYPTION_KEY → hardcoded fallback
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    encryption_key: str = Field(default="", alias="APP_ENCRYPTION_KEY")

    @property
    def jwt_secret_resolved(self) -> str:
        """Resolve JWT secret: JWT_SECRET > APP_ENCRYPTION_KEY > hardcoded fallback."""
        if self.jwt_secret:
            return self.jwt_secret
        if self.encryption_key:
            return self.encryption_key
        return "hexaveil-cms-default-jwt-secret-change-in-production"

    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_ttl: int = Field(default=86400, alias="JWT_TTL")  # 24h, matches PHP

    # Bedolaga Bot API
    bedolaga_api_url: str = Field(default="", alias="BEDOLAGA_API_URL")
    bedolaga_api_token: str = Field(default="", alias="BEDOLAGA_API_TOKEN")

    # Crypto (for finance secrets, compatible with PHP Crypto.php)
    app_encryption_key: str = Field(default="", alias="APP_ENCRYPTION_KEY")

    # CORS
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    # Uploads
    upload_dir: str = Field(default="/var/www/html/public/uploads", alias="UPLOAD_DIR")
    public_dir: str = Field(default="/var/www/html/public", alias="PUBLIC_DIR")
    root_path: str = Field(default="/var/www/html", alias="ROOT_PATH")
    max_upload_size: int = Field(default=64 * 1024 * 1024, alias="MAX_UPLOAD_SIZE")  # 64MB


@lru_cache
def get_cms_settings() -> CmsSettings:
    """Cached settings singleton (same pattern as remnawave)."""
    return CmsSettings()