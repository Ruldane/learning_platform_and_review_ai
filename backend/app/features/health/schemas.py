from typing import Literal

from pydantic import BaseModel

from app.providers.health import HealthStatus


class HealthReport(BaseModel):
    """`down` si la base échoue, `degraded` si un autre contrôle échoue, sinon `ok`."""

    status: Literal["ok", "degraded", "down"]
    checks: dict[str, HealthStatus]
