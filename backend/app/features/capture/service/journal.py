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

from app.core.errors import AppError
from app.db.models.study import JournalEntry, JournalKind
from app.features.capture.repository import JournalRepository
from app.features.capture.schemas import JournalEntryOut, JournalLinksOut, JournalPage


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


async def entry_by_ref(db: AsyncSession, user_id: str, ref_key: str) -> JournalEntry | None:
    """La ligne de cette clé (« capture:{session} »…), `None` si elle n'est pas encore écrite."""
    return await JournalRepository(db, user_id).by_ref(ref_key)


def invalid_cursor() -> AppError:
    return AppError("invalid_cursor", "Curseur du journal inconnu.", 422)


def _out(row: JournalEntry) -> JournalEntryOut:
    """`data` n'est jamais rendu tel quel (texte du Tuteur, faits du bilan, concepts)."""
    return JournalEntryOut(
        id=row.id,
        kind=row.kind,  # type: ignore[arg-type]  # colonne texte, valeurs de JournalKind
        text=row.text,
        occurred_on=row.occurred_on,
        created_at=row.created_at,
        links=JournalLinksOut(
            session_id=row.session_id,
            study_session_id=row.study_session_id,
            quiz_attempt_id=row.quiz_attempt_id,
            memory_item_id=row.memory_item_id,
        ),
    )


async def journal_page(
    db: AsyncSession, user_id: str, *, kind: JournalKind | None, before: str | None, limit: int
) -> JournalPage:
    """Le journal de l'utilisateur, le plus récent d'abord (`kind` : un genre seulement) ;
    `before` : id de la dernière ligne déjà lue, 422 `invalid_cursor` s'il n'est pas à lui."""
    rows = await JournalRepository(db, user_id).page(kind, before, limit + 1)
    if rows is None:
        raise invalid_cursor()
    shown = rows[:limit]
    more = len(rows) > limit
    return JournalPage(
        entries=[_out(row) for row in shown], next_before=shown[-1].id if more else None
    )
