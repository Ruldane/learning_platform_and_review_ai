from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.db.base import new_id
from app.features.conversations.service import (
    BRAIN_SCOPE,
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
    ConversationThread,
    TurnOptions,
    ensure_conversation,
    preferred_chat,
    read_conversation,
    require_chat,
    submit_turn,
)
from app.mcp.recorder import ACTIVE


async def _thread(
    db: AsyncSession, user_id: str, conversation_id: UUID | None
) -> ConversationThread:
    if conversation_id is not None:
        selected = await require_chat(db, user_id, BRAIN_SCOPE, str(conversation_id))
        return ConversationThread(selected.id, BRAIN_SCOPE, selected.subject_id)
    legacy = ConversationThread.for_subject(user_id, BRAIN_SCOPE, user_id)
    row = await preferred_chat(db, user_id, BRAIN_SCOPE, legacy.id)
    if row is None:
        return legacy
    return ConversationThread(row.id, BRAIN_SCOPE, row.subject_id)


async def read_brain_chat(
    db: AsyncSession, user_id: str, conversation_id: UUID | None = None
) -> ConversationOut | None:
    thread = await _thread(db, user_id, conversation_id)
    return await read_conversation(db, user_id, thread.id)


async def create_brain_chat(db: AsyncSession, user_id: str) -> ConversationOut:
    thread_id = new_id()
    await ensure_conversation(db, user_id, ConversationThread(thread_id, BRAIN_SCOPE, thread_id))
    if recorder := ACTIVE.get():
        await recorder.persist_in(db)
    result = await read_conversation(db, user_id, thread_id)
    assert result is not None
    return result


async def ask_brain(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    body: ConversationQuestionIn,
    conversation_id: UUID | None = None,
) -> ConversationStarted:
    thread = await _thread(db, user_id, conversation_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        # Seul le chemin historique peut créer son fil à la première question.
        if conversation_id is not None or thread.subject_id != user_id:
            await require_chat(tx, user_id, BRAIN_SCOPE, thread.id)
        return TurnOptions()

    return await submit_turn(runner, db, user_id, thread, body, authorize)
