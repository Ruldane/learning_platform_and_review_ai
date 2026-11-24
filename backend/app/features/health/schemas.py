from typing import Literal

from pydantic import BaseModel

from app.providers.health import HealthStatus


class HealthReport(BaseModel):
    """`down` if the database fails, `degraded` if another check fails, otherwise `ok`."""

    status: Literal["ok", "degraded", "down"]
    checks: dict[str, HealthStatus]


class EmbeddingProgress(BaseModel):
    """The embeddings model: present, or being downloaded (`percent` from 0 to 100, empty
    while the size is unknown). `detail` is a plain-language text without personal data."""

    model: str
    present: bool
    percent: int | None
    detail: str
