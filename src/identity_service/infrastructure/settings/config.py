from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseModel):
    uri: str = "mongodb://localhost:27017/?directConnection=true"
    database: str = "identity_db"
    min_pool_size: int = Field(default=0, ge=0)
    max_pool_size: int = Field(default=20, ge=1)
    server_selection_timeout_ms: int = Field(default=5000, ge=100)
    operation_timeout_ms: int = Field(default=10000, ge=100)


class JwtSettings(BaseModel):
    private_key_pem: str | None = None
    private_key_path: Path | None = None
    issuer: str = "https://identity.vehicle-resale.local"
    audience: str = "vehicle-resale-backend"
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)

    def require_private_key_pem(self) -> str:
        if self.private_key_pem:
            return self.private_key_pem
        if self.private_key_path is not None:
            return self.private_key_path.read_text()
        raise ValueError("jwt private key material is required")


class CorsSettings(BaseModel):
    allowed_origins: list[str] = Field(default_factory=list)
    allowed_methods: list[str] = Field(default_factory=lambda: ["*"])
    allowed_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = False


class LogSettings(BaseModel):
    level: str = "INFO"


class RateLimitSettings(BaseModel):
    login_limit: int = Field(default=10, ge=1)
    register_limit: int = Field(default=10, ge=1)
    window_seconds: float = Field(default=60.0, gt=0)


class SecuritySettings(BaseModel):
    max_request_body_bytes: int = Field(default=65536, ge=1024)


class BootstrapSettings(BaseModel):
    admin_email: str | None = None
    admin_password: str | None = None
    admin_full_name: str = "Platform Administrator"
    admin_document: str = "PLATFORMADMIN001"
    admin_phone: str = "+15550000001"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IDENTITY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = "development"
    service_name: str = "identity-service"
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    logging: LogSettings = Field(default_factory=LogSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    bootstrap: BootstrapSettings = Field(default_factory=BootstrapSettings)
