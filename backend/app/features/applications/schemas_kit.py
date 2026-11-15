"""Schémas du kit de candidature (SPEC 6.4, F16, D143) : les sept pièces d'une fiche, dans l'ordre
fixe de `KIT_ORDER`. Une 422 nomme les champs, jamais le texte envoyé (une pièce est une donnée
personnelle)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.agents.tools.kit_schema import KIT_KINDS as KIT_ORDER
from app.db.models.applications import KitKind as KitKind
from app.db.models.applications import KitStatus as KitStatus

CONTENT_MAX = 20_000
# `KIT_ORDER` : l'ordre fixe des pièces (F16), celui de la liste et des fichiers de l'archive.
__all__ = [
    "KIT_ORDER",
    "KitItemOut",
    "KitKind",
    "KitOut",
    "KitPatch",
    "KitSourceOut",
    "KitStartOut",
    "KitStatus",
]


class KitSourceOut(BaseModel):
    """Une page lue pour le dossier de l'entreprise. `rank` : son numéro dans le texte (`[rank]`),
    depuis 1."""

    rank: int = Field(ge=1)
    url: str
    title: str | None


class KitItemOut(BaseModel):
    """Une pièce. `id` : `artifact_id` de l'événement `artifact.ready` (vide tant que la pièce n'est
    pas rangée, statut `pending`). `flags` : les termes que le profil ne dit pas (pièce « à
    vérifier »). `salary_fields` : les réponses salariales laissées à January. `words` : le compte
    des mots (le message pour `linkedin`, les deux relances ensemble pour `followups`). `error` :
    le motif lisible d'une pièce en échec. `sources` : les pages du dossier (`company_brief`)."""

    id: str | None
    kind: KitKind
    status: KitStatus
    content: str
    flags: list[str]
    salary_fields: int
    words: int | None
    error: str | None
    sources: list[KitSourceOut]
    edited: bool
    updated_at: datetime | None


class KitOut(BaseModel):
    """Le kit d'une fiche : toujours sept pièces, `pending` pour celles pas encore rangées.
    `session_id` : la session ouverte, sinon la dernière ; `running` : une session est ouverte."""

    session_id: str | None
    running: bool
    items: list[KitItemOut]


class KitStartOut(BaseModel):
    session_id: str


class KitPatch(BaseModel):
    """Le texte de January pour la pièce (vide permis : la pièce redevient « à vérifier »)."""

    content: Annotated[str, Field(max_length=CONTENT_MAX)]
