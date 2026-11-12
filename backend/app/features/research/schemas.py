"""Schémas de l'API de la recherche web : compteur Brave du mois et sources d'une session."""

from pydantic import BaseModel, ConfigDict

from app.db.models.research import PageStatus, SourceKind, SourceVerdict

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "BraveUsageOut",
    "PageStatus",
    "SearchUsageOut",
    "SourceKind",
    "SourceOut",
    "SourceVerdict",
]


class BraveUsageOut(BaseModel):
    """Requêtes Brave du mois civil UTC (`month` : « AAAA-MM ») pour la clé en vigueur."""

    has_key: bool
    used: int
    cap: int
    month: str


class SearchUsageOut(BaseModel):
    brave: BraveUsageOut


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str | None
    author: str | None
    lang: str | None
    published: str | None
    status: PageStatus
    verdict: SourceVerdict
    score: int | None
    reason: str | None
    kind: SourceKind  # `person` : praticien repéré par l'Éclaireur (phase 4, D82)
