"""Contrat des contrôles de santé : un contrôle par service, sans dépendance aux features."""

from typing import Protocol

import httpx
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """État d'un service. `detail` est en français et ne contient jamais de secret."""

    ok: bool
    detail: str


class HealthCheck(Protocol):
    """Un contrôle nommé. `check` peut lever : le service de santé le transforme en échec."""

    name: str

    async def check(self) -> HealthStatus: ...


def available() -> HealthStatus:
    return HealthStatus(ok=True, detail="Disponible")


def unexpected_status(response: httpx.Response) -> HealthStatus:
    return HealthStatus(ok=False, detail=f"Réponse inattendue : HTTP {response.status_code}")
