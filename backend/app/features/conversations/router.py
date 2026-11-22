from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.conversations.classroom import ask_classroom, read_classroom
from app.features.conversations.schemas import (
    ConversationMessageIn,
    ConversationStarted,
    LessonConversationOut,
)
from app.features.conversations.service import ask_lesson_professor, read_lesson_conversation

router = APIRouter(tags=["conversations"])


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
