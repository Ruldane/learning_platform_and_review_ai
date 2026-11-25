"""Contract of the health checks: one check per service, with no dependency on the features."""

from typing import Protocol

import httpx
from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Service health. The detail is in English and never contains a secret."""

    ok: bool
    detail: str


class HealthCheck(Protocol):
    """A named check. `check` may raise: the health service turns it into a failure."""

    name: str

    async def check(self) -> HealthStatus: ...


def available() -> HealthStatus:
    return HealthStatus(ok=True, detail="Available")


def unexpected_status(response: httpx.Response) -> HealthStatus:
    return HealthStatus(ok=False, detail=f"Unexpected response (HTTP {response.status_code})")
