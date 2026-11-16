"""Contrat du fil d'activité (SPEC 14.2, P15, D163) : ce que les agents et les tâches de fond ont
fait, sans contenu inventé. Le texte est écrit par le code, jamais par un modèle."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ActivityKind = Literal["lesson", "radar", "brief", "memory", "project", "job_failed"]


class ActivityItem(BaseModel):
    """Un événement. `id` est stable (`{kind}:{ref}:{état}`) : le front ne montre pas deux fois le
    même ; `link` est une route du front."""

    id: str
    kind: ActivityKind
    at: datetime
    title: str
    detail: str | None = None
    link: str | None = None


class ActivityPage(BaseModel):
    """Les événements, le plus récent d'abord. `latest_at` : l'instant du plus récent d'entre eux
    (`None` sans événement), à rendre en `after` au prochain passage."""

    items: list[ActivityItem]
    latest_at: datetime | None
