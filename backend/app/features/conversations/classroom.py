"""One classroom thread per ready lesson, independent of the Professor's thread."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.agents.tools.conversation_port import CLASSROOM_SCOPE
from app.features.conversations.lesson_context import lesson_material, lesson_version, ready_lesson
from app.features.conversations.schemas import (
    ConversationMessageIn,
    ConversationStarted,
    LessonConversationOut,
)
from app.features.conversations.service import (
    ConversationThread,
    TurnOptions,
    read_conversation,
    submit_turn,
)


async def read_classroom(
    db: AsyncSession, user_id: str, lesson_id: str
) -> LessonConversationOut | None:
    await ready_lesson(db, user_id, lesson_id)
    thread = ConversationThread.for_subject(user_id, CLASSROOM_SCOPE, lesson_id)
    stored = await read_conversation(db, user_id, thread.id)
    if stored is None:
        return None
    return LessonConversationOut.model_validate({**stored.model_dump(), "lesson_id": lesson_id})


async def ask_classroom(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    lesson_id: str,
    message: ConversationMessageIn,
) -> ConversationStarted:
    await ready_lesson(db, user_id, lesson_id)
    thread = ConversationThread.for_subject(user_id, CLASSROOM_SCOPE, lesson_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        _, markdown = await ready_lesson(tx, user_id, lesson_id)
        if message.passage is not None:
            lesson_material(markdown, message.passage, message.passage_occurrence)
        return TurnOptions(lesson_version=lesson_version(markdown), mode=CLASSROOM_SCOPE)

    return await submit_turn(runner, db, user_id, thread, message, authorize)
