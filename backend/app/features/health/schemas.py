from typing import Literal

from pydantic import BaseModel

from app.providers.health import HealthStatus


class HealthReport(BaseModel):
    """`down` si la base échoue, `degraded` si un autre contrôle échoue, sinon `ok`."""

    status: Literal["ok", "degraded", "down"]
    checks: dict[str, HealthStatus]


class EmbeddingProgress(BaseModel):
    """Le modèle d'embeddings : présent, ou en cours de téléchargement (`percent` de 0 à 100, vide
    tant que la taille n'est pas connue). `detail` est un texte français sans donnée personnelle."""

    model: str
    present: bool
    percent: int | None
    detail: str
