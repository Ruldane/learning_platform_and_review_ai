from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_providers
from app.core.providers import Providers
from app.features.health.schemas import HealthReport
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
