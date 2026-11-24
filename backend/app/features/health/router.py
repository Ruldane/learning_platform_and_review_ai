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
    """Always 200 and without authentication: the front end reads `status`."""
    return await service.run()


@router.get("/health/embedding", response_model=EmbeddingProgress)
async def embedding_progress(
    providers: Annotated[Providers, Depends(get_providers)],
) -> EmbeddingProgress:
    """Progress of the embeddings model (`bge-m3`): public, like `/health`. If the model
    is missing, the back end downloads it from Ollama, one download at a time (restarted after a
    failure)."""
    if providers.embedding is None:  # never in production: `build_providers` always sets it
        raise AppError("not_implemented", "Not available yet.", 501)
    data = await providers.embedding.progress()
    return EmbeddingProgress(
        model=data.model, present=data.present, percent=data.percent, detail=data.detail
    )
