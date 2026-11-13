"""Schémas de la capture rapide et du journal (SPEC F18, D108). Une 422 ne recopie jamais la saisie
(gestionnaire commun : chemins et messages seulement)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models.study import JournalKind

__all__ = [
    "CaptureRequest",
    "CaptureStarted",
    "JournalEntryOut",
    "JournalKind",
    "JournalLinksOut",
    "JournalPage",
]

TEXT_MAX = 20_000
URL_MAX = 2048


class CaptureRequest(BaseModel):
    """Une seule source : un lien http(s), un texte, ou un document déjà importé
    (`POST /documents`). Zéro ou plusieurs : 422 `invalid_input`."""

    url: str | None = Field(default=None, max_length=URL_MAX)
    text: str | None = Field(default=None, max_length=TEXT_MAX)
    document_id: str | None = Field(default=None, max_length=36)


class CaptureStarted(BaseModel):
    session_id: str


class JournalLinksOut(BaseModel):
    session_id: str | None
    study_session_id: str | None
    quiz_attempt_id: str | None
    memory_item_id: str | None


class JournalEntryOut(BaseModel):
    id: str
    kind: JournalKind
    text: str
    occurred_on: date  # jour de January (son fuseau, D98)
    created_at: datetime
    links: JournalLinksOut


class JournalPage(BaseModel):
    """Les lignes, les plus récentes d'abord ; `next_before` : curseur de la page suivante
    (`?before=`), `None` à la dernière."""

    entries: list[JournalEntryOut]
    next_before: str | None
