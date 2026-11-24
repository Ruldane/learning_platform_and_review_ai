from collections.abc import Sequence
from unicodedata import combining, normalize
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.agents.tools.conversation_port import ConversationPractice, ConversationSource
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.conversations import Conversation
from app.features.conversations.lesson_context import ready_lesson
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.schemas import ChatScope, ConversationSummary
from app.mcp.recorder import ACTIVE

CHAT_SCOPES = frozenset({"brain", "training"})


def conversation_not_found() -> AppError:
    return AppError("conversation_not_found", "Conversation introuvable.", 404)


def conversation_busy() -> AppError:
    return AppError(
        "conversation_busy", "A reply is already in progress in this conversation.", 409
    )


def _summary(row: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=UUID(row.id),
        title=row.title or "Nouvelle conversation",
        updated_at=row.updated_at,
    )


def _search_text(text: str) -> str:
    return "".join(char for char in normalize("NFD", text.casefold()) if not combining(char))


async def list_chats(
    db: AsyncSession, user_id: str, scope: ChatScope, query: str = ""
) -> list[ConversationSummary]:
    needle = _search_text(query.strip())
    summaries = [_summary(row) for row in await ConversationRepository(db, user_id).recent(scope)]
    return [summary for summary in summaries if needle in _search_text(summary.title)]


async def require_chat(
    db: AsyncSession, user_id: str, scope: ChatScope, thread_id: str
) -> Conversation:
    row = await ConversationRepository(db, user_id).by_scope(scope, thread_id)
    if row is None:
        raise conversation_not_found()
    return row


async def preferred_chat(
    db: AsyncSession, user_id: str, scope: ChatScope, legacy_id: str
) -> Conversation | None:
    return await ConversationRepository(db, user_id).preferred(scope, legacy_id)


async def rename_chat(
    db: AsyncSession, user_id: str, scope: ChatScope, thread_id: str, title: str
) -> ConversationSummary:
    rows = await ConversationRepository(db, user_id).claim(scope, thread_id)
    if not rows:
        raise conversation_not_found()
    row = rows[0]
    row.title, row.updated_at = title, utcnow()
    if recorder := ACTIVE.get():
        await recorder.persist_in(db)
    return _summary(row)


async def erase_chat(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    scope: ChatScope,
    thread_id: str | None = None,
    *,
    keep_thread: bool = False,
) -> None:
    repo = ConversationRepository(db, user_id)
    threads = await repo.claim(scope, thread_id)
    if thread_id is not None and not threads:
        raise conversation_not_found()
    turns = TurnRepository(db, user_id)
    sessions: list[str] = []
    for thread in threads:
        for turn, status in await turns.turns(thread.id):
            if status in OPEN_SESSION_STATES or runner.is_active(turn.session_id):
                raise conversation_busy()
            sessions.append(turn.session_id)
    await runner.delete_threads(sessions)
    await turns.erase_sessions(sessions)
    thread_ids = [thread.id for thread in threads]
    await repo.erase_chat_snapshots(thread_ids, sessions)
    if scope == "training" and not keep_thread:
        await repo.cancel_erased_training(thread_ids, utcnow())
    for thread in threads:
        if keep_thread:
            thread.updated_at = utcnow()
        else:
            await db.delete(thread)


async def checked_lesson_ids(
    db: AsyncSession, user_id: str, lesson_ids: Sequence[UUID]
) -> list[str]:
    ids = list(dict.fromkeys(str(lesson_id) for lesson_id in lesson_ids))
    for lesson_id in ids:
        await ready_lesson(db, user_id, lesson_id)
    return ids


async def cited_study_material(
    db: AsyncSession, user_id: str, thread_id: str
) -> tuple[set[str], list[ConversationPractice]]:
    lessons: set[str] = set()
    cards: list[ConversationPractice] = []
    for turn, status in await TurnRepository(db, user_id).turns(thread_id):
        if status != "completed":
            continue
        sources = [ConversationSource.model_validate(source) for source in turn.sources]
        cited = {str(source.id) for source in sources if source.kind == "lesson"}
        for raw in turn.practice or []:
            card = ConversationPractice.model_validate(raw)
            if str(card.lesson_id) in cited:
                cards.append(card)
        lessons.update(cited)
    return lessons, cards
