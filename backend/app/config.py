from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Les ports sont publiés sur 127.0.0.1 : l'interface s'ouvre aussi bien par `localhost` que par
# `127.0.0.1`, et le navigateur envoie l'une ou l'autre origine.
_LOOPBACK_TWINS = {"localhost": "127.0.0.1", "127.0.0.1": "localhost"}


def _with_loopback_twin(origin: str) -> list[str]:
    host = urlsplit(origin).hostname or ""
    twin = _LOOPBACK_TWINS.get(host)
    return [origin, origin.replace(f"//{host}", f"//{twin}", 1)] if twin else [origin]


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
    # Échéance totale d'un appel à un modèle, en secondes (voir `LLM_CALL_DEADLINE_S`, D115).
    llm_call_deadline_s: float = Field(default=600.0, gt=0)

    qdrant_url: str = "http://qdrant:6333"
    # Adresse du tableau de bord de Qdrant vue du navigateur (lien des statistiques, D67).
    qdrant_dashboard_url: str = "http://localhost:6333/dashboard"
    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "bge-m3"
    embedding_dimension: int = 1024
    memory_collection: str = "memory"
    searxng_url: str = "http://searxng:8080"
    gotenberg_url: str = "http://gotenberg:3000"
    # Repli Gotenberg du lecteur web (page rendue en JavaScript, D72) : `false` le coupe.
    web_render_fallback: bool = True
    # Tâches planifiées (leçons « J-7 », D91) : `false` ne démarre pas le planificateur (tests).
    scheduler_enabled: bool = True

    # Une origine ou plusieurs séparées par des virgules ; voir `cors_origins`.
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
    def cors_origins(self) -> list[str]:
        """Origines autorisées : celles de `cors_origin`, plus la forme jumelle de chaque origine
        locale (`localhost` <-> `127.0.0.1`, même port). Sans doublon, ordre conservé."""
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
