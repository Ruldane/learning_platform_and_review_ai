from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.brain.service.chat import ask_brain, read_brain_chat
from app.features.conversations.service import (
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
)

router = APIRouter(prefix="/conversation")


@router.get("")
async def read_conversation(db: Db, user: CurrentUserDep) -> ConversationOut | None:
    return await read_brain_chat(db, user.id)


@router.post("/messages", status_code=202)
async def message(
    body: ConversationQuestionIn,
    db: Db,
    user: CurrentUserDep,
    runtime: RuntimeDep,
) -> ConversationStarted:
    return await ask_brain(runtime.runner, db, user.id, body)
