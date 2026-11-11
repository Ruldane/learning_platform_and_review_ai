from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application, lue depuis l'environnement (et `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    # Vide = calculée à partir de `data_dir` (voir `_default_database_url`) : jamais vide ensuite.
    database_url: str = ""
    auth_mode: Literal["local", "google"] = "local"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    zai_api_key: str | None = None
    brave_api_key: str | None = None
    zai_base_url: str = "https://api.z.ai/api/paas/v4/"

    qdrant_url: str = "http://qdrant:6333"
    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "bge-m3"
    searxng_url: str = "http://searxng:8080"
    gotenberg_url: str = "http://gotenberg:3000"

    cors_origin: str = "http://localhost:5173"

    google_client_id: str | None = None
    google_client_secret: str | None = None
    allowed_emails: str | None = None

    @model_validator(mode="after")
    def _default_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite+aiosqlite:///{(self.data_dir / 'app.db').as_posix()}"
        return self

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
