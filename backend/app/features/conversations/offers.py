from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.db.base import new_id
from app.features.conversations.chats import conversation_not_found, require_chat
from app.features.conversations.schemas import (
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
)
from app.features.conversations.service import (
    ConversationThread,
    TurnOptions,
    ensure_conversation,
    read_conversation,
    submit_turn,
)

OFFERS_SCOPE: Final = "offers"


async def create_offers_chat(db: AsyncSession, user_id: str) -> ConversationOut:
    thread_id = new_id()
    await ensure_conversation(db, user_id, ConversationThread(thread_id, OFFERS_SCOPE, thread_id))
    return await read_offers_chat(db, user_id, UUID(thread_id))


async def read_offers_chat(
    db: AsyncSession, user_id: str, conversation_id: UUID
) -> ConversationOut:
    thread_id = str(conversation_id)
    await require_chat(db, user_id, OFFERS_SCOPE, thread_id)
    thread = await read_conversation(db, user_id, thread_id)
    if thread is None:
        raise conversation_not_found()
    return thread


async def ask_offers_chat(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    conversation_id: UUID,
    body: ConversationQuestionIn,
) -> ConversationStarted:
    row = await require_chat(db, user_id, OFFERS_SCOPE, str(conversation_id))
    thread = ConversationThread(row.id, OFFERS_SCOPE, row.subject_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        await require_chat(tx, user_id, OFFERS_SCOPE, thread.id)
        return TurnOptions()

    return await submit_turn(runner, db, user_id, thread, body, authorize)
