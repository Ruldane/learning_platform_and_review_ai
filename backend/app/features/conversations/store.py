from collections.abc import Sequence
from contextlib import nullcontext
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.conversation_port import (
    ConversationContext,
    ConversationExchange,
    ConversationSource,
)
from app.core.errors import AppError
from app.db.models.conversations import Conversation, ConversationTurn
from app.features.conversations.lesson_context import (
    lesson_material,
    lesson_version,
    ready_lesson,
    stale_passage,
)
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.service import LESSON_SCOPE
from app.mcp.recorder import ChangeRecorder

MAX_HISTORY = 4
MAX_HISTORY_FIELD = 800


def _check_version(markdown: str, turn: ConversationTurn) -> None:
    if turn.lesson_version is not None and turn.lesson_version != lesson_version(markdown):
        raise stale_passage()


async def _owned_turn(
    repo: TurnRepository, session_id: str, thread_id: str, turn_id: str
) -> tuple[Conversation, ConversationTurn]:
    turn = await repo.get(turn_id)
    thread = await ConversationRepository(repo.session, repo.user_id).get(thread_id)
    if (
        turn is None
        or thread is None
        or turn.thread_id != thread_id
        or turn.session_id != session_id
    ):
        raise AppError("conversation_turn_not_found", "Tour de conversation introuvable.", 404)
    return thread, turn


class AgentConversationStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ConversationContext | None:
        async with self._factory() as db:
            repo = TurnRepository(db, user_id)
            thread, turn = await _owned_turn(repo, session_id, thread_id, turn_id)
            if turn.answer is not None:
                return None
            if thread.scope != LESSON_SCOPE:
                raise AppError(
                    "conversation_scope_unknown", "Ce type de fil est indisponible.", 409
                )
            title, markdown = await ready_lesson(db, user_id, thread.subject_id)
            history = await repo.history(turn, MAX_HISTORY)
            used = await repo.used_tokens(session_id)
        _check_version(markdown, turn)
        exchanges = [
            ConversationExchange(row.question[:MAX_HISTORY_FIELD], row.answer[:MAX_HISTORY_FIELD])
            for row in history
            if row.answer is not None
        ]
        material = lesson_material(markdown, turn.passage, turn.passage_occurrence)
        source = ConversationSource(
            kind="lesson", id=UUID(thread.subject_id), title=title, excerpt=turn.passage
        )
        return ConversationContext(turn.question, turn.strong, exchanges, material, source, used)

    async def save_reply(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        answer: str,
        sources: Sequence[ConversationSource],
    ) -> None:
        async with self._factory() as db:
            repo = TurnRepository(db, user_id)
            turn = await repo.claim_reply(thread_id, turn_id, session_id)
            if turn is None:
                return
            if turn.lesson_version is not None:
                thread, _ = await _owned_turn(repo, session_id, thread_id, turn_id)
                _, markdown = await ready_lesson(db, user_id, thread.subject_id)
                _check_version(markdown, turn)
            recorder = (
                ChangeRecorder(self._factory, turn.mcp_call_id, user_id)
                if turn.mcp_call_id is not None
                else None
            )
            async with recorder if recorder is not None else nullcontext():
                turn.answer = answer
                turn.sources = [source.model_dump(mode="json") for source in sources]
                if recorder is not None:
                    await recorder.extend_in(db, keep_latest=frozenset())
            await db.commit()
