from collections.abc import Callable

import pytest
from fastapi import FastAPI

from app.core.deps import get_providers
from app.core.providers import Providers
from app.providers.health import HealthCheck, HealthStatus


class FakeCheck:
    def __init__(self, name: str, status: HealthStatus) -> None:
        self.name = name
        self._status = status

    async def check(self) -> HealthStatus:
        return self._status


class RaisingCheck:
    def __init__(self, name: str, error: Exception) -> None:
        self.name = name
        self._error = error

    async def check(self) -> HealthStatus:
        raise self._error


def override_health_checks(app: FastAPI, checks: list[HealthCheck]) -> None:
    """Remplace les contrôles réels : la route ne touche aucun service."""
    real: Providers = app.state.providers

    def fake_providers() -> Providers:
        return Providers(
            llm=real.llm,
            llm_factory=real.llm_factory,
            cipher=real.cipher,
            env_keys=real.env_keys,
            key_providers=real.key_providers,
            health_checks=checks,
        )

    app.dependency_overrides[get_providers] = fake_providers


@pytest.fixture
def override_checks(app: FastAPI, client: object) -> Callable[[list[HealthCheck]], None]:
    # Dépend de `client` : `app.state.providers` n'existe qu'après le démarrage (lifespan).
    def apply(checks: list[HealthCheck]) -> None:
        override_health_checks(app, checks)

    return apply
