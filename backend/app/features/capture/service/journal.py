"""Chronological journal (SPEC F18, D99): captures, study sessions, quizzes, weekly reviews.

This module is the journal's only writer; the other features call it through their service
(contract 2). A write is idempotent per `ref_key`: a replay returns the id of the row already
written. The commit belongs to the caller.

Application logs: never a row's text, only ids (17.4).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.study import JournalEntry, JournalKind
from app.features.capture.repository import JournalRepository
from app.features.capture.schemas import JournalEntryOut, JournalLinksOut, JournalPage


@dataclass(frozen=True)
class JournalLinks:
    """The objects the row points to (all optional)."""

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
    """Writes a journal row and returns its id; if `ref_key` already exists for this user,
    returns the id of the existing row (the first write wins)."""
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
    """The row of this key ("capture:{session}"...), `None` if it is not written yet."""
    return await JournalRepository(db, user_id).by_ref(ref_key)


def invalid_cursor() -> AppError:
    return AppError("invalid_cursor", "Unknown journal cursor.", 422)


def _out(row: JournalEntry) -> JournalEntryOut:
    """`data` is never returned as is (Tutor text, review facts, concepts)."""
    study_kind: Literal["guided", "training"] = (
        "training" if row.data.get("kind") == "training" else "guided"
    )
    quiz_id = row.data.get("quiz_id") if row.kind == "quiz" else None
    ide_links = row.data if row.kind == "ide_check" else {}
    ide_session, ide_run = ide_links.get("ide_session_id"), ide_links.get("ide_run_id")
    return JournalEntryOut(
        id=row.id,
        kind=row.kind,  # type: ignore[arg-type]  # colonne texte, valeurs de JournalKind
        text=row.text,
        occurred_on=row.occurred_on,
        created_at=row.created_at,
        links=JournalLinksOut(
            session_id=row.session_id,
            study_session_id=row.study_session_id,
            study_session_kind=study_kind if row.study_session_id is not None else None,
            quiz_attempt_id=row.quiz_attempt_id,
            quiz_id=quiz_id if isinstance(quiz_id, str) else None,
            ide_session_id=ide_session if isinstance(ide_session, str) else None,
            ide_run_id=ide_run if isinstance(ide_run, str) else None,
            memory_item_id=row.memory_item_id,
        ),
    )


async def journal_page(
    db: AsyncSession, user_id: str, *, kind: JournalKind | None, before: str | None, limit: int
) -> JournalPage:
    """The user's journal, most recent first (`kind`: a single kind only); `before`: id of the
    last row already read, 422 `invalid_cursor` if it is not theirs."""
    rows = await JournalRepository(db, user_id).page(kind, before, limit + 1)
    if rows is None:
        raise invalid_cursor()
    shown = rows[:limit]
    more = len(rows) > limit
    return JournalPage(
        entries=[_out(row) for row in shown], next_before=shown[-1].id if more else None
    )
