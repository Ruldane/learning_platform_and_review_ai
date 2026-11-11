"""Composition de l'application : l'unique module qui assemble les implémentations concrètes
(fournisseurs LLM, sondes de santé) avec les features. Le lifespan l'appelle au démarrage."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import httpx
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.costs import ModelPrice, load_prices
from app.agents.runtime.run_settings import RunSettingsSource
from app.config import Settings
from app.core.providers import MemoryProviders, Providers
from app.core.security import Cipher
from app.features.health.checks import DatabaseCheck, LlmKeysCheck
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.settings.keys_service import DbKeyReader
from app.features.settings.service import SettingsModelReader, SettingsRunReader
from app.providers.embeddings.ollama import OllamaEmbedder
from app.providers.embeddings.ollama_probe import OllamaProbe
from app.providers.health import HealthCheck
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.llm.glm import GlmProvider
from app.providers.llm.registry import LLM_PROVIDERS, PRICES_PATH
from app.providers.pdf.extract import PdfPlumberExtractor
from app.providers.pdf.gotenberg_probe import GotenbergProbe
from app.providers.search.searxng_probe import SearxngProbe
from app.providers.storage.local import LocalFileStorage
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.vector.qdrant_probe import QdrantProbe
from app.providers.web.base import FETCH_TIMEOUT_S
from app.providers.web.fetch import SafeHttpFetcher, refuse_all_cookies
from app.providers.web.reader import TrafilaturaWebReader
from app.providers.web.transport import GuardedTransport
from app.providers.web.youtube import TranscriptApiYoutube

_OLLAMA_TIMEOUT_SECONDS = 60.0
_QDRANT_TIMEOUT_SECONDS = 10


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


def model_prices() -> dict[str, ModelPrice]:
    """Table des prix des modèles (`model_prices.json` des fournisseurs) pour le suivi des coûts :
    lue ici car `app.agents` n'importe pas `app.providers.llm.registry` (contrat 3)."""
    return load_prices(PRICES_PATH)


def run_settings_source(session_factory: async_sessionmaker[AsyncSession]) -> RunSettingsSource:
    """Réglages lus par le moteur d'agents, adaptés du service de la feature `settings` : le
    moteur n'importe aucune feature (contrat 6)."""
    return SettingsRunReader(session_factory)


def _reader_http() -> httpx.AsyncClient:
    """Client du lecteur web, à part de celui d'Ollama : connexion sur l'adresse vérifiée
    (`GuardedTransport`, anti rebinding DNS), jamais de redirection automatique (la garde SSRF
    revérifie chaque saut), aucun proxy ni réglage de l'environnement (l'adresse connectée
    serait celle du proxy), aucun cookie retenu (client partagé entre utilisateurs)."""
    return httpx.AsyncClient(
        transport=GuardedTransport(),
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(FETCH_TIMEOUT_S),
        cookies=refuse_all_cookies(),
    )


@asynccontextmanager
async def memory_providers(settings: Settings) -> AsyncIterator[MemoryProviders]:
    """Embeddings Ollama, index Qdrant, stockage local, extraction PDF, lecteur web et YouTube ;
    les clients sont fermés à la sortie. Aucune requête à la construction : le back démarre même
    si Ollama ou Qdrant sont arrêtés (la collection est créée à la première utilisation)."""
    async with (
        httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT_SECONDS) as http,
        _reader_http() as reader_http,
    ):
        # Pas de contrôle de version au démarrage : il ferait une requête dès la construction.
        qdrant = AsyncQdrantClient(
            url=settings.qdrant_url, timeout=_QDRANT_TIMEOUT_SECONDS, check_compatibility=False
        )
        try:
            embedder = OllamaEmbedder(settings.ollama_base_url, settings.embedding_model, http)
            index = QdrantMemoryRepository(
                qdrant,
                embedder,
                collection=settings.memory_collection,
                dimension=settings.embedding_dimension,
            )
            pdf = PdfPlumberExtractor()
            web = TrafilaturaWebReader(SafeHttpFetcher(reader_http), pdf)
            yield MemoryProviders(
                embedder=embedder,
                index=index,
                storage=LocalFileStorage(settings.storage_dir),
                pdf=pdf,
                web=web,
                youtube=TranscriptApiYoutube(web),
            )
        finally:
            await qdrant.close()


@asynccontextmanager
async def open_memory_runtime(
    session_factory: async_sessionmaker[AsyncSession], providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    """Ce que la mémoire partage entre les requêtes (indexeur, verrous), construit sur les
    fournisseurs de `memory_providers` ou ceux qu'un test a injectés."""
    async with memory_runtime(session_factory, providers) as runtime:
        yield runtime
