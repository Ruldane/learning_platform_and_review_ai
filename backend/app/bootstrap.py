"""Composition de l'application : l'unique module qui assemble les implémentations concrètes
(fournisseurs LLM, sondes de santé) avec les features. Le lifespan l'appelle au démarrage."""

from collections.abc import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.providers import Providers
from app.core.security import Cipher
from app.features.health.checks import DatabaseCheck, LlmKeysCheck
from app.features.settings.keys_service import DbKeyReader
from app.features.settings.service import SettingsModelReader
from app.providers.embeddings.ollama_probe import OllamaProbe
from app.providers.health import HealthCheck
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.llm.glm import GlmProvider
from app.providers.llm.registry import LLM_PROVIDERS
from app.providers.pdf.gotenberg_probe import GotenbergProbe
from app.providers.search.searxng_probe import SearxngProbe
from app.providers.vector.qdrant_probe import QdrantProbe


def _health_checks(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    http: httpx.AsyncClient,
    llm_keys: LlmKeysCheck,
) -> list[HealthCheck]:
    return [
        DatabaseCheck(session_factory),
        QdrantProbe(settings.qdrant_url, http),
        OllamaProbe(settings.ollama_base_url, settings.embedding_model, http),
        SearxngProbe(settings.searxng_url, http),
        GotenbergProbe(settings.gotenberg_url, http),
        llm_keys,
    ]


def build_providers(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    cipher: Cipher,
    http: httpx.AsyncClient,
    local_user_id: Callable[[], str | None],
) -> Providers:
    """`http` est partagé par les sondes (créé et fermé par le lifespan) ; `local_user_id` est
    lu à chaque contrôle car l'utilisateur local n'existe qu'après la construction."""
    # GLM : l'adresse Z.ai configurée sert aussi au test de clé et à la liste des modèles.
    llm: dict[str, LlmProvider] = {
        **LLM_PROVIDERS,
        "glm": GlmProvider(base_url=settings.zai_base_url),
    }
    env_keys: dict[str, str | None] = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "glm": settings.zai_api_key,
    }
    factory = LlmFactory(
        SettingsModelReader(session_factory),
        DbKeyReader(session_factory, cipher, env_keys),
        llm,
        {"glm": settings.zai_base_url},
    )
    llm_keys = LlmKeysCheck(session_factory, cipher, env_keys, llm, local_user_id)
    return Providers(
        llm=llm,
        llm_factory=factory,
        cipher=cipher,
        env_keys=env_keys,
        health_checks=_health_checks(settings, session_factory, http, llm_keys),
    )
