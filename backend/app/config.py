from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.portfolio_urls import normalize_origin

# The ports are published on 127.0.0.1: the interface opens just as well via `localhost` as
# via `127.0.0.1`, and the browser sends one or the other origin.
_LOOPBACK_TWINS = {"localhost": "127.0.0.1", "127.0.0.1": "localhost"}


def _with_loopback_twin(origin: str) -> list[str]:
    host = urlsplit(origin).hostname or ""
    twin = _LOOPBACK_TWINS.get(host)
    return [origin, origin.replace(f"//{host}", f"//{twin}", 1)] if twin else [origin]


class Settings(BaseSettings):
    """Application configuration, read from the environment (and `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    # Empty = computed from `data_dir` (see `_default_database_url`): never empty afterwards.
    database_url: str = ""
    auth_mode: Literal["local", "google"] = "local"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    zai_api_key: str | None = None
    brave_api_key: str | None = None
    zai_base_url: str = "https://api.z.ai/api/paas/v4/"
    # Total deadline of one model call, in seconds (see `LLM_CALL_DEADLINE_S`, D115).
    llm_call_deadline_s: float = Field(default=600.0, gt=0)

    qdrant_url: str = "http://qdrant:6333"
    # Address of the Qdrant dashboard as seen from the browser (statistics link, D67).
    qdrant_dashboard_url: str = "http://localhost:6333/dashboard"
    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "bge-m3"
    embedding_dimension: int = 1024
    memory_collection: str = "memory"
    searxng_url: str = "http://searxng:8080"
    gotenberg_url: str = "http://gotenberg:3000"
    # Gotenberg fallback of the web reader (page rendered in JavaScript, D72): `false` turns it off.
    web_render_fallback: bool = True
    # Scheduled tasks (« J-7 » lessons, D91): `false` does not start the scheduler (tests).
    scheduler_enabled: bool = True

    # One origin or several separated by commas; see `cors_origins`.
    cors_origin: str = "http://localhost:5173"

    google_client_id: str | None = None
    google_client_secret: str | None = None
    # Deployment attestation: Google revokes the tokens at the OAuth project level.
    calendar_google_dedicated_project: bool = False
    calendar_google_client_id: str | None = None
    calendar_google_client_secret: SecretStr | None = None
    calendar_google_redirect_uri: str | None = None
    allowed_emails: str | None = None
    # Google addresses (authorization endpoint, `token` endpoint, expected issuer): Google's
    # defaults; the fake provider of the tests replaces them (P5, phase 9).
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_issuer: str = "https://accounts.google.com"
    # Return address registered with Google, and the front-end address the user returns to (P10).
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_url: str = "http://localhost:5173"
    portfolio_public_origin: str | None = Field(default=None, max_length=105)
    # Fixed length of a sign-in session, in days, counted from the sign-in (P6).
    session_days: int = Field(default=30, ge=1, le=90)

    # Phase 10: exchange folder shared with the sandbox (named volume, P5) and maximum size of the
    # body of a call to the MCP server, in bytes (P10).
    sandbox_spool_dir: Path = Path("/spool")
    mcp_body_limit: int = Field(default=1_000_000, ge=1_000)
    # Daily limits of the MCP server, per token (P17, D311): 0 turns the limit off.
    mcp_writes_per_day: int = Field(default=100, ge=0)
    mcp_calls_per_day: int = Field(default=1_000, ge=0)

    @field_validator("portfolio_public_origin")
    @classmethod
    def _portfolio_origin(cls, value: str | None) -> str | None:
        return normalize_origin(value)

    @model_validator(mode="after")
    def _default_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite+aiosqlite:///{(self.data_dir / 'app.db').as_posix()}"
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Allowed origins: those of `cors_origin`, plus the twin form of each local origin
        (`localhost` <-> `127.0.0.1`, same port). No duplicates, order kept."""
        origins: list[str] = []
        for raw in self.cors_origin.split(","):
            origin = raw.strip().rstrip("/")
            for candidate in _with_loopback_twin(origin) if origin else []:
                if candidate not in origins:
                    origins.append(candidate)
        return origins

    @property
    def checkpoints_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def secret_path(self) -> Path:
        return self.data_dir / "secret.key"

    @property
    def storage_dir(self) -> Path:
        return self.data_dir / "storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()
