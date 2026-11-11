from fastapi import APIRouter

from app.features.auth.router import router as auth_router
from app.features.health.router import router as health_router
from app.features.sessions.router import router as sessions_router
from app.features.settings.keys_router import router as keys_router
from app.features.settings.router import router as settings_router

# Chaque feature ajoute ici son routeur ; `create_app` les monte sous `/api/v1`.
FEATURE_ROUTERS: list[APIRouter] = [
    auth_router,
    settings_router,
    keys_router,
    health_router,
    sessions_router,
]
