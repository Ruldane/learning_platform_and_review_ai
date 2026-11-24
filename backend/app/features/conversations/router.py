from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, RuntimeDep
from app.features.conversations.chats import erase_chat, list_chats, rename_chat
from app.features.conversations.classroom import ask_classroom, read_classroom
from app.features.conversations.offers import ask_offers_chat, create_offers_chat, read_offers_chat
from app.features.conversations.schemas import (
    ChatScope,
    ConversationMessageIn,
    ConversationOut,
    ConversationQuestionIn,
    ConversationRename,
    ConversationStarted,
    ConversationSummary,
    LessonConversationOut,
)
from app.features.conversations.service import ask_lesson_professor, read_lesson_conversation

router = APIRouter(tags=["conversations"])


@router.get("/conversations/{scope}")
async def list_conversations(
    scope: ChatScope, db: Db, user: CurrentUserDep, q: Annotated[str, Query(max_length=120)] = ""
) -> list[ConversationSummary]:
    return await list_chats(db, user.id, scope, q)


@router.patch("/conversations/{scope}/{conversation_id}")
async def rename_conversation(
    scope: ChatScope, conversation_id: UUID, body: ConversationRename, db: Db, user: CurrentUserDep
) -> ConversationSummary:
    return await rename_chat(db, user.id, scope, str(conversation_id), body.title)


@router.delete("/conversations/{scope}/{conversation_id}/messages", status_code=204)
async def clear_conversation(
    scope: ChatScope, conversation_id: UUID, db: Db, user: ConfirmedUserDep, runtime: RuntimeDep
) -> None:
    await erase_chat(runtime.runner, db, user.id, scope, str(conversation_id), keep_thread=True)


@router.delete("/conversations/{scope}/{conversation_id}", status_code=204)
async def delete_conversation(
    scope: ChatScope, conversation_id: UUID, db: Db, user: ConfirmedUserDep, runtime: RuntimeDep
) -> None:
    await erase_chat(runtime.runner, db, user.id, scope, str(conversation_id))


@router.delete("/conversations/{scope}", status_code=204)
async def wipe_conversations(
    scope: ChatScope, db: Db, user: ConfirmedUserDep, runtime: RuntimeDep
) -> None:
    await erase_chat(runtime.runner, db, user.id, scope)


@router.post("/conversations/offers", status_code=201)
async def create_offers_conversation(db: Db, user: CurrentUserDep) -> ConversationOut:
    return await create_offers_chat(db, user.id)


@router.get("/conversations/offers/{conversation_id}")
async def read_offers_conversation(
    conversation_id: UUID, db: Db, user: CurrentUserDep
) -> ConversationOut:
    return await read_offers_chat(db, user.id, conversation_id)


@router.post("/conversations/offers/{conversation_id}/messages", status_code=202)
async def post_offers_message(
    conversation_id: UUID,
    body: ConversationQuestionIn,
    db: Db,
    user: CurrentUserDep,
    runtime: RuntimeDep,
) -> ConversationStarted:
    return await ask_offers_chat(runtime.runner, db, user.id, conversation_id, body)


@router.get("/lessons/{lesson_id}/conversation")
async def read_professor(
    lesson_id: UUID, db: Db, user: CurrentUserDep
) -> LessonConversationOut | None:
    return await read_lesson_conversation(db, user.id, str(lesson_id))


@router.post("/lessons/{lesson_id}/conversation/messages", status_code=202)
async def ask_professor(
    lesson_id: UUID,
    message: ConversationMessageIn,
    db: Db,
    user: CurrentUserDep,
    runtime: RuntimeDep,
) -> ConversationStarted:
    return await ask_lesson_professor(runtime.runner, db, user.id, str(lesson_id), message)


@router.get("/lessons/{lesson_id}/classroom")
async def get_classroom(
    lesson_id: UUID, db: Db, user: CurrentUserDep
) -> LessonConversationOut | None:
    return await read_classroom(db, user.id, str(lesson_id))


@router.post("/lessons/{lesson_id}/classroom/messages", status_code=202)
async def post_classroom_message(
    lesson_id: UUID,
    message: ConversationMessageIn,
    db: Db,
    user: CurrentUserDep,
    runtime: RuntimeDep,
) -> ConversationStarted:
    return await ask_classroom(runtime.runner, db, user.id, str(lesson_id), message)
