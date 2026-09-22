from pathlib import Path
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "EVENT HQ Backend API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, testing, production
    
    # JWT Authentication - MUST be explicitly configured in .env or environment
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # Database URL
    DATABASE_URL: str = "sqlite:///./event_hq.db"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        if v.startswith("sqlite:///"):
            raw_path = v[len("sqlite:///"):]
            if raw_path == ":memory:" or raw_path.startswith("?"):
                return v
            if raw_path.startswith("./") or raw_path.startswith(".\\"):
                raw_path = raw_path[2:]
            # Check if relative path (not absolute like C:/ or /)
            if not (len(raw_path) > 1 and raw_path[1] == ":") and not raw_path.startswith("/"):
                resolved = (BACKEND_DIR / raw_path).resolve()
                return f"sqlite:///{resolved.as_posix()}"
        return v
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Tournament Metadata Defaults
    EVENT_NAME: str = "EVENT HQ · BMSIT 2026"
    DEFAULT_TABLE_COUNT: int = 32
    
    # Google Forms Webhook Integration
    GOOGLE_FORMS_WEBHOOK_SECRET: str = ""
    
    # Initial Admin Seed Configuration (Optional - set in .env to auto-seed)
    INITIAL_ORGANIZER_EMAIL: str = ""
    INITIAL_ORGANIZER_PASSWORD: str = ""
    INITIAL_ORGANIZER_NAME: str = "Lead Organizer"

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        # Strict validation: SECRET_KEY must never be empty or shorter than 32 characters
        if not self.SECRET_KEY or len(self.SECRET_KEY.strip()) < 32:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be explicitly configured "
                "via environment variable or .env file, and must contain at least 32 characters. "
                "Automatic insecure fallback secrets are disabled."
            )
        return self

    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Note: In test execution or CLI, environment variables can be provided before instantiating Settings
try:
    settings = Settings()
except Exception:
    # If no .env exists during direct module discovery, provide fallback for test/cli discovery
    import os
    if (
        os.environ.get("ENVIRONMENT") == "testing"
        or "pytest" in os.environ.get("_", "")
        or os.environ.get("IS_CLI") == "1"
    ):
        if not os.environ.get("SECRET_KEY"):
            os.environ["SECRET_KEY"] = "default_fallback_secret_key_minimum_32_characters_length_ok"
        settings = Settings()
    else:
        raise