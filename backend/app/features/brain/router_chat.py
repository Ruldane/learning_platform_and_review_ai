from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.brain.service.chat import ask_brain, create_brain_chat, read_brain_chat
from app.features.conversations.service import (
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
)

router = APIRouter()


@router.post("/conversations", status_code=201)
async def create_conversation(db: Db, user: CurrentUserDep) -> ConversationOut:
    return await create_brain_chat(db, user.id)


@router.get("/conversation")
async def read_conversation(
    db: Db, user: CurrentUserDep, conversation_id: UUID | None = None
) -> ConversationOut | None:
    return await read_brain_chat(db, user.id, conversation_id)


@router.post("/conversation/messages", status_code=202)
async def message(
    body: ConversationQuestionIn,
    db: Db,
    user: CurrentUserDep,
    runtime: RuntimeDep,
    conversation_id: UUID | None = None,
) -> ConversationStarted:
    return await ask_brain(runtime.runner, db, user.id, body, conversation_id)
