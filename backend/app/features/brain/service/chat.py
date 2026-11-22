from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.features.conversations.service import (
    BRAIN_SCOPE,
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
    ConversationThread,
    TurnOptions,
    read_conversation,
    submit_turn,
)


def _thread(user_id: str) -> ConversationThread:
    return ConversationThread.for_subject(user_id, BRAIN_SCOPE, user_id)


async def read_brain_chat(db: AsyncSession, user_id: str) -> ConversationOut | None:
    return await read_conversation(db, user_id, _thread(user_id).id)


async def _authorize(_: AsyncSession) -> TurnOptions:
    # Le fil est personnel, sans sujet imposé ni identifiant fourni par le client.
    return TurnOptions()


async def ask_brain(
    runner: SessionRunner, db: AsyncSession, user_id: str, body: ConversationQuestionIn
) -> ConversationStarted:
    return await submit_turn(runner, db, user_id, _thread(user_id), body, _authorize)
