import asyncio
from typing import Literal

import httpx

from app.features.health.schemas import HealthReport
from app.providers.health import HealthCheck, HealthStatus

CHECK_TIMEOUT_SECONDS = 3.0
DB_CHECK = "db"


async def _run_one(check: HealthCheck, timeout: float) -> HealthStatus:
    """Un contrôle ne fait jamais échouer le rapport. Seul le nom du type d'exception est
    rapporté : le message d'une exception réseau peut contenir une adresse ou une clé."""
    try:
        return await asyncio.wait_for(check.check(), timeout)
    except (TimeoutError, httpx.TimeoutException):
        return HealthStatus(ok=False, detail="Délai dépassé")
    except Exception as exc:
        return HealthStatus(ok=False, detail=f"Erreur : {type(exc).__name__}")


class HealthService:
    def __init__(self, checks: list[HealthCheck], timeout: float = CHECK_TIMEOUT_SECONDS) -> None:
        self._checks = checks
        self._timeout = timeout

    async def run(self) -> HealthReport:
        statuses = await asyncio.gather(*(_run_one(c, self._timeout) for c in self._checks))
        results = {c.name: s for c, s in zip(self._checks, statuses, strict=True)}
        status: Literal["ok", "degraded", "down"]
        if DB_CHECK in results and not results[DB_CHECK].ok:
            status = "down"
        elif all(s.ok for s in results.values()):
            status = "ok"
        else:
            status = "degraded"
        return HealthReport(status=status, checks=results)
