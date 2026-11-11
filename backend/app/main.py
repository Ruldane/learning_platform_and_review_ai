import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.bootstrap import build_providers
from app.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.security import Cipher, KnownSecrets, load_or_create_secret
from app.db.engine import create_engine, create_session_factory
from app.features.auth.service import AuthService
from app.features.registry import FEATURE_ROUTERS

API_PREFIX = "/api/v1"
logger = logging.getLogger(__name__)
_LOG_LEVEL = "INFO"
_PROBE_TIMEOUT_SECONDS = 3.0


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
        # Client partagé par les sondes de santé.
        http = await stack.enter_async_context(httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECONDS))
        app.state.providers = build_providers(
            app.state.settings,
            app.state.session_factory,
            app.state.cipher,
            http,
            lambda: getattr(app.state, "local_user_id", None),
        )
        if app.state.settings.auth_mode == "local":
            await _ensure_local_user(app)
        yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construit l'application. `settings` prime toujours sur le cache `get_settings()`."""
    settings = settings if settings is not None else get_settings()
    app = FastAPI(
        title="Tremplin",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    # Ordre important : le dernier middleware ajouté est le plus externe. Les erreurs sont
    # enregistrées d'abord pour que leur 500 traverse CORS (voir `UnexpectedErrorMiddleware`).
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    return app
