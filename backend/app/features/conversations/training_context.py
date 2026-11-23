from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.conversation_port import ConversationReference, ConversationSource
from app.core.errors import AppError
from app.db.models.conversations import ConversationTurn
from app.features.conversations.lesson_context import lesson_excerpt, ready_lesson
from app.features.lessons.service.conversation import lesson_terms


async def selected_refs(db: AsyncSession, turn: ConversationTurn) -> list[ConversationReference]:
    terms = lesson_terms(turn.question)
    refs = []
    for lesson_id in turn.lesson_ids or []:
        try:
            title, markdown = await ready_lesson(db, turn.user_id, lesson_id)
        except AppError as error:
            if error.code not in {"lesson_not_found", "lesson_not_ready"}:
                raise
            continue
        material = lesson_excerpt(markdown, terms)
        source = ConversationSource(
            kind="lesson", id=UUID(lesson_id), title=title, excerpt=material[:400]
        )
        refs.append(ConversationReference(source, material, primary=True))
    return refs
