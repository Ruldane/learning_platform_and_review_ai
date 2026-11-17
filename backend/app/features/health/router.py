from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_providers
from app.core.errors import AppError
from app.core.providers import Providers
from app.features.health.schemas import EmbeddingProgress, HealthReport
from app.features.health.service import HealthService

router = APIRouter(tags=["health"])


def get_health_service(providers: Annotated[Providers, Depends(get_providers)]) -> HealthService:
    return HealthService(providers.health_checks)


@router.get("/health", response_model=HealthReport)
async def health(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthReport:
    """Toujours 200 et sans authentification : le front lit `status`."""
    return await service.run()


@router.get("/health/embedding", response_model=EmbeddingProgress)
async def embedding_progress() -> EmbeddingProgress:
    """Progression du modèle d'embeddings (`bge-m3`) : public, comme `/health`. Si le modèle
    manque, le back le télécharge depuis Ollama, une seule fois par processus."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)
