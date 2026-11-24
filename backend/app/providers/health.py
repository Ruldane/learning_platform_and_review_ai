"""Contrat des contrôles de santé : un contrôle par service, sans dépendance aux features."""

from typing import Protocol

import httpx
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Service health. The detail is in English and never contains a secret."""

    ok: bool
    detail: str


class HealthCheck(Protocol):
    """Un contrôle nommé. `check` peut lever : le service de santé le transforme en échec."""

    name: str

    async def check(self) -> HealthStatus: ...


def available() -> HealthStatus:
    return HealthStatus(ok=True, detail="Available")


def unexpected_status(response: httpx.Response) -> HealthStatus:
    return HealthStatus(ok=False, detail=f"Unexpected response (HTTP {response.status_code})")
