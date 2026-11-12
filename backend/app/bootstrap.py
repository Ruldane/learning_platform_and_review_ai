"""Composition de l'application : l'unique module qui assemble les implémentations concrètes
(fournisseurs LLM, sondes de santé) avec les features. Le lifespan l'appelle au démarrage."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext

import httpx
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.costs import ModelPrice, load_prices
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.tools.memory_port import MemoryGateway
from app.agents.tools.web_port import WebGateway
from app.config import Settings
from app.core.providers import MemoryProviders, Providers, ResearchProviders
from app.core.security import Cipher
from app.features.health.checks import DatabaseCheck, LlmKeysCheck
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.keys_service import DbKeyReader
from app.features.settings.service import SettingsModelReader, SettingsRunReader
from app.providers.embeddings.ollama import OllamaEmbedder
from app.providers.embeddings.ollama_probe import OllamaProbe
from app.providers.health import HealthCheck
from app.providers.keys import KeyProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.llm.glm import GlmProvider
from app.providers.llm.registry import LLM_PROVIDERS, PRICES_PATH
from app.providers.pdf.base import PageRenderer
from app.providers.pdf.gotenberg import GotenbergRenderer
from app.providers.pdf.gotenberg_probe import GotenbergProbe
from app.providers.pdf.subprocess import SubprocessPdfExtractor
from app.providers.search.base import SEARCH_TIMEOUT_S, SearchProvider
from app.providers.search.brave import BraveKeyProvider, BraveSearch
from app.providers.search.searxng import SearxngSearch
from app.providers.search.searxng_probe import SearxngProbe
from app.providers.storage.local import LocalFileStorage
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.vector.qdrant_probe import QdrantProbe
from app.providers.web.arxiv import ArxivReader
from app.providers.web.base import FETCH_TIMEOUT_S, WebReader
from app.providers.web.fetch import SafeHttpFetcher, refuse_all_cookies
from app.providers.web.github import GithubReader
from app.providers.web.reader import TrafilaturaWebReader
from app.providers.web.routing import RoutingWebReader
from app.providers.web.throttle import DomainThrottle
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
    *,
    key_http: httpx.AsyncClient,
) -> Providers:
    """`http` sert aux sondes de santé, `key_http` (`key_test_http`) au test de la clé Brave ;
    tous deux créés et fermés par le lifespan. `local_user_id` est lu à chaque contrôle car
    l'utilisateur local n'existe qu'après la construction."""
    # GLM : l'adresse Z.ai configurée sert aussi au test de clé et à la liste des modèles.
    llm: dict[str, LlmProvider] = {
        **LLM_PROVIDERS,
        "glm": GlmProvider(base_url=settings.zai_base_url),
    }
    env_keys: dict[str, str | None] = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "glm": settings.zai_api_key,
        "brave": settings.brave_api_key,
    }
    factory = LlmFactory(
        SettingsModelReader(session_factory),
        DbKeyReader(session_factory, cipher, env_keys),
        llm,
        {"glm": settings.zai_base_url},
    )
    llm_keys = LlmKeysCheck(session_factory, cipher, env_keys, llm, local_user_id)
    # Écran des clés : les LLM puis Brave, qui n'est ni dans la fabrique ni dans les modèles.
    key_providers: dict[str, KeyProvider] = {**llm, "brave": BraveKeyProvider(key_http)}
    return Providers(
        llm=llm,
        llm_factory=factory,
        cipher=cipher,
        env_keys=env_keys,
        key_providers=key_providers,
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


def memory_gateway(runtime: MemoryRuntime) -> MemoryGateway:
    """Mémoire vue par le moteur d'agents (outils `memory_*`, Archiviste), adaptée du service de la
    feature `memory` : le moteur n'importe aucune feature (contrat 6, D68)."""
    return AgentMemoryGateway(runtime)


def web_gateway(runtime: ResearchRuntime) -> WebGateway:
    """Recherche web vue par le moteur d'agents (outils `web_*`, Éclaireur), adaptée du service de
    la feature `research` : le moteur n'importe aucune feature (contrat 6, D77)."""
    return AgentWebGateway(runtime)


def agent_ports(memory: MemoryRuntime, research: ResearchRuntime) -> AgentPorts:
    """Tous les ports du moteur d'agents (D82) : un port de plus = un champ d'`AgentPorts` et
    une ligne ici."""
    return AgentPorts(memory=memory_gateway(memory), web=web_gateway(research))


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


def _render_http() -> httpx.AsyncClient:
    """Client de Gotenberg, à part : aucun proxy ni réglage de l'environnement, aucune
    redirection, 15 s (délai d'une page, D63). Ouvert par `memory_providers` (D74)."""
    return httpx.AsyncClient(
        follow_redirects=False, trust_env=False, timeout=httpx.Timeout(FETCH_TIMEOUT_S)
    )


def page_renderer(settings: Settings, http: httpx.AsyncClient) -> PageRenderer | None:
    """Repli Gotenberg du lecteur web, `None` si `WEB_RENDER_FALLBACK=false`."""
    if not settings.web_render_fallback:
        return None
    return GotenbergRenderer(http, settings.gotenberg_url)


def _render_client(
    settings: Settings,
) -> AbstractAsyncContextManager[httpx.AsyncClient | None]:
    """Client de Gotenberg seulement si le repli est actif (aucun client ouvert inutilisé)."""
    return _render_http() if settings.web_render_fallback else nullcontext(None)


def _web_reader(
    settings: Settings,
    reader_http: httpx.AsyncClient,
    render_http: httpx.AsyncClient | None,
    pdf: SubprocessPdfExtractor,
) -> WebReader:
    """Lecteur web étendu (D74) : un seul fetcher sûr et un seul débit par hôte pour tout le
    processus (pages, API GitHub, API et PDF arXiv) ; repli Gotenberg selon les réglages. La
    mémoire (import d'URL), YouTube (repli) et la recherche reçoivent ce même lecteur."""
    fetcher = SafeHttpFetcher(reader_http, throttle=DomainThrottle())
    renderer = page_renderer(settings, render_http) if render_http is not None else None
    pages = TrafilaturaWebReader(fetcher, pdf, renderer=renderer)
    return RoutingWebReader(pages, GithubReader(fetcher), ArxivReader(fetcher, pdf))


@asynccontextmanager
async def memory_providers(settings: Settings) -> AsyncIterator[MemoryProviders]:
    """Embeddings Ollama, index Qdrant, stockage local, extraction PDF, lecteur web et YouTube ;
    les clients sont fermés à la sortie. Aucune requête à la construction : le back démarre même
    si Ollama ou Qdrant sont arrêtés (la collection est créée à la première utilisation)."""
    async with (
        httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT_SECONDS) as http,
        _reader_http() as reader_http,
        _render_client(settings) as render_http,
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
            # Sous-processus borné (délai, mémoire, 2 au plus) : import de documents et lecteur web.
            pdf = SubprocessPdfExtractor()
            web = _web_reader(settings, reader_http, render_http, pdf)
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


@asynccontextmanager
async def open_research_runtime(
    session_factory: async_sessionmaker[AsyncSession],
    research: ResearchProviders,
    providers: Providers,
) -> AsyncIterator[ResearchRuntime]:
    """Ce que la recherche web partage entre les requêtes et les agents (verrous, lecteur de
    clés), sur les fournisseurs de `research_providers` ou ceux qu'un test a injectés. La clé
    Brave est lue comme celles des LLM : réglages d'abord, puis `.env`."""
    keys = DbKeyReader(session_factory, providers.cipher, providers.env_keys)
    yield ResearchRuntime(session_factory, research, keys)


def key_test_http() -> httpx.AsyncClient:
    """Client du test de la clé Brave (écran des clés), ouvert par le lifespan : comme
    `_search_http`, aucun proxy ni réglage de l'environnement (la clé ne passe par aucun
    intermédiaire, revue 3.3, D74), aucune redirection, 10 s."""
    return _search_http()


def _search_http() -> httpx.AsyncClient:
    """Client d'un fournisseur de recherche (SearXNG ou Brave), un par fournisseur : hôte fixe
    et configuré, donc sans la garde SSRF du lecteur web (D63) ; aucun proxy ni réglage de
    l'environnement (SearXNG est sur le réseau interne, la clé Brave ne passe par aucun
    intermédiaire), aucune redirection, 10 s."""
    return httpx.AsyncClient(
        follow_redirects=False, trust_env=False, timeout=httpx.Timeout(SEARCH_TIMEOUT_S)
    )


@asynccontextmanager
async def research_providers(
    settings: Settings, web: WebReader
) -> AsyncIterator[ResearchProviders]:
    """SearXNG (`settings.searxng_url`) et la fabrique Brave (une instance par clé, client
    partagé), sur le lecteur web de la mémoire ; clients fermés à la sortie. Aucune requête à
    la construction."""
    async with _search_http() as searxng_http, _search_http() as brave_http:

        def brave(api_key: str) -> SearchProvider:
            return BraveSearch(brave_http, api_key)

        yield ResearchProviders(
            searxng=SearxngSearch(searxng_http, settings.searxng_url), brave=brave, web=web
        )
