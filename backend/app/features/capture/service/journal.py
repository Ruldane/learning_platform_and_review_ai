"""Journal chronologique (SPEC F18, D99) : captures, sessions d'étude, quiz, bilans hebdomadaires.

Ce module est le seul écrivain du journal ; les autres features l'appellent par leur service
(contrat 2). Une écriture est idempotente par `ref_key` : un rejeu rend l'id de la ligne déjà
écrite. Le commit appartient à l'appelant.

Journaux de l'application : jamais le texte d'une ligne, seulement des identifiants (17.4).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.study import JournalKind
from app.features.capture.repository import JournalRepository


@dataclass(frozen=True)
class JournalLinks:
    """Les objets auxquels la ligne renvoie (tous facultatifs)."""

    session_id: str | None = None
    study_session_id: str | None = None
    quiz_attempt_id: str | None = None
    memory_item_id: str | None = None


NO_LINKS = JournalLinks()
NO_DATA: Mapping[str, Any] = MappingProxyType({})


async def add_entry(
    db: AsyncSession,
    user_id: str,
    *,
    kind: JournalKind,
    text: str,
    occurred_on: date,
    ref_key: str | None,
    links: JournalLinks = NO_LINKS,
    data: Mapping[str, Any] = NO_DATA,
) -> str:
    """Écrit une ligne du journal et rend son id ; si `ref_key` existe déjà pour cet
    utilisateur, rend l'id de la ligne existante (la première écriture gagne)."""
    return await JournalRepository(db, user_id).insert_once(
        ref_key,
        kind=kind,
        text=text,
        occurred_on=occurred_on,
        session_id=links.session_id,
        study_session_id=links.study_session_id,
        quiz_attempt_id=links.quiz_attempt_id,
        memory_item_id=links.memory_item_id,
        data=dict(data),
    )
