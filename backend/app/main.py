import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.agents.runtime.lifespan import agent_runtime
from app.agents.runtime.openapi import register_event_schemas
from app.bootstrap import (
    build_providers,
    key_test_http,
    memory_gateway,
    model_prices,
    open_memory_runtime,
    run_settings_source,
)
from app.bootstrap import memory_providers as open_memory_providers
from app.bootstrap import research_providers as open_research_providers
from app.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.limits import BodySizeLimit
from app.core.logging import configure_logging
from app.core.providers import MemoryProviders, ResearchProviders
from app.core.security import Cipher, KnownSecrets, load_or_create_secret
from app.db.engine import create_engine, create_session_factory
from app.features.auth.service import AuthService
from app.features.memory.service.upload import MAX_UPLOAD_BYTES
from app.features.registry import FEATURE_ROUTERS

API_PREFIX = "/api/v1"
logger = logging.getLogger(__name__)
_LOG_LEVEL = "INFO"
_PROBE_TIMEOUT_SECONDS = 3.0
# Corps d'un import : le fichier (20 Mo) plus l'enveloppe multipart et les autres champs.
_UPLOAD_BODY_MAX = MAX_UPLOAD_BYTES + 1024 * 1024


async def _ensure_local_user(app: FastAPI) -> None:
    """Mode `local` : crée l'utilisateur unique s'il manque et mémorise son id."""
    try:
        async with app.state.session_factory() as session:
            user = await AuthService(session).ensure_local_user()
            await session.commit()
            app.state.local_user_id = user.id
    except OperationalError as exc:
        if "no such table" not in str(exc.orig):
            raise
        message = (
            "Base de données non initialisée : lance `alembic upgrade head` avant de démarrer."
        )
        logger.error(message)
        raise RuntimeError(message) from exc


def _setup_security(app: FastAPI) -> None:
    """Secret de l'application, chiffreur, et masquage des clés dans les journaux."""
    settings: Settings = app.state.settings
    app.state.cipher = Cipher(load_or_create_secret(settings.secret_path))
    for key in (
        settings.anthropic_api_key,
        settings.openai_api_key,
        settings.zai_api_key,
        settings.brave_api_key,
    ):
        if key:
            KnownSecrets.add(key)
    configure_logging(_LOG_LEVEL, KnownSecrets.values)


async def _open_external_providers(app: FastAPI, stack: AsyncExitStack) -> MemoryProviders:
    """Fournisseurs de la mémoire puis de la recherche web : ceux qu'on a injectés (tests),
    sinon la composition réelle, fermée par la pile. La recherche reprend le lecteur web de la
    mémoire. Rend les fournisseurs de la mémoire."""
    memory: MemoryProviders | None = app.state.injected_memory_providers
    if memory is None:
        memory = await stack.enter_async_context(open_memory_providers(app.state.settings))
    app.state.memory_providers = memory
    research: ResearchProviders | None = app.state.injected_research_providers
    if research is None:
        research = await stack.enter_async_context(
            open_research_providers(app.state.settings, memory.web)
        )
    app.state.research_providers = research
    return memory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    _setup_security(app)
    # Le schéma n'est jamais créé ici : en Docker, l'entrypoint lance `alembic upgrade head`.
    # La pile ferme le moteur et le client HTTP même si la composition ou le démarrage échoue.
    async with AsyncExitStack() as stack:
        engine = create_engine(app.state.settings.database_url)
        stack.push_async_callback(engine.dispose)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        # Client partagé par les sondes de santé ; le test de la clé Brave a le sien (D74).
        http = await stack.enter_async_context(httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECONDS))
        key_http = await stack.enter_async_context(key_test_http())
        app.state.providers = build_providers(
            app.state.settings,
            app.state.session_factory,
            app.state.cipher,
            http,
            lambda: getattr(app.state, "local_user_id", None),
            key_http=key_http,
        )
        # Avant la mémoire : son worker relit la base au démarrage ; un schéma absent doit donner
        # l'indication `alembic upgrade head` plutôt qu'une erreur SQL brute.
        if app.state.settings.auth_mode == "local":
            await _ensure_local_user(app)
        injected = await _open_external_providers(app, stack)
        # Mémoire : entrée avant le moteur d'agents (qui s'en servira), donc fermée après lui.
        app.state.memory = await stack.enter_async_context(
            open_memory_runtime(app.state.session_factory, injected)
        )
        # Moteur d'agents (bus, runner, checkpointer) : entré après le moteur de base, donc
        # fermé avant lui (la pile dépile à l'envers) ; reprend les sessions interrompues.
        app.state.runtime = await stack.enter_async_context(
            agent_runtime(
                app.state.settings,
                app.state.session_factory,
                app.state.providers.llm_factory,
                model_prices(),
                run_settings_source(app.state.session_factory),
                memory=memory_gateway(app.state.memory),
            )
        )
        yield


def create_app(
    settings: Settings | None = None,
    *,
    memory_providers: MemoryProviders | None = None,
    research_providers: ResearchProviders | None = None,
) -> FastAPI:
    """Construit l'application. `settings` prime toujours sur le cache `get_settings()` ;
    `memory_providers` remplace la composition réelle d'Ollama et de Qdrant, et
    `research_providers` celle de SearXNG et de Brave (tests)."""
    settings = settings if settings is not None else get_settings()
    app = FastAPI(
        title="Tremplin",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.injected_memory_providers = memory_providers
    app.state.injected_research_providers = research_providers
    # Ordre important : le dernier middleware ajouté est le plus externe. Les erreurs sont
    # enregistrées d'abord pour que leur 500 traverse CORS (voir `UnexpectedErrorMiddleware`).
    register_error_handlers(app)
    # Entre la gestion des erreurs et CORS : la 413 traverse CORS (lisible par le navigateur).
    app.add_middleware(BodySizeLimit, path=f"{API_PREFIX}/documents", max_bytes=_UPLOAD_BODY_MAX)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_event_schemas(app)
    return app
