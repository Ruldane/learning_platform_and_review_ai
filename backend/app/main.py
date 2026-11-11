from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.features.registry import FEATURE_ROUTERS

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construit l'application. `settings` prime toujours sur le cache `get_settings()`."""
    settings = settings if settings is not None else get_settings()
    app = FastAPI(
        title="Tremplin",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    return app
