"""Health wiring (`GET /health`): service probes and the LLM key check. `app.bootstrap` calls it
when it assembles the providers."""

from collections.abc import Callable, Mapping

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.security import Cipher
from app.features.health.checks import DatabaseCheck, LlmKeysCheck
from app.providers.embeddings.base import EmbeddingProgressSource
from app.providers.embeddings.ollama_probe import OllamaProbe
from app.providers.embeddings.ollama_pull import OllamaPullWatcher
from app.providers.health import HealthCheck
from app.providers.llm.base import LlmProvider
from app.providers.pdf.gotenberg_probe import GotenbergProbe
from app.providers.search.searxng_probe import SearxngProbe
from app.providers.vector.qdrant_probe import QdrantProbe


def health_checks(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    http: httpx.AsyncClient,
    cipher: Cipher,
    env_keys: Mapping[str, str | None],
    llm: Mapping[str, LlmProvider],
    local_user_id: Callable[[], str | None],
) -> list[HealthCheck]:
    """Database, services, then LLM keys. Google mode: the key check does not depend on any local
    user (`local_user_id` is then irrelevant)."""
    llm_keys = LlmKeysCheck(
        session_factory,
        cipher,
        env_keys,
        llm,
        local_user_id,
        google_mode=settings.auth_mode == "google",
    )
    return [
        DatabaseCheck(session_factory),
        QdrantProbe(settings.qdrant_url, http),
        OllamaProbe(settings.ollama_base_url, settings.embedding_model, http),
        SearxngProbe(settings.searxng_url, http),
        GotenbergProbe(settings.gotenberg_url, http),
        llm_keys,
    ]


def embedding_progress(settings: Settings, http: httpx.AsyncClient) -> EmbeddingProgressSource:
    """Progress (and download, if missing) of the embeddings model, for
    `GET /health/embedding` (P13)."""
    return OllamaPullWatcher(settings.ollama_base_url, settings.embedding_model, http)
