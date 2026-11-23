from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.creation import PrepareSession
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.conversation_port import CONVERSATION_GRAPH, TURN_TOKEN_LIMIT
from app.agents.tools.feynman_port import FEYNMAN_SCOPES
from app.core.clock import local_moment, local_today, user_zone
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT
from app.db.base import new_id
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.conversations import Conversation, ConversationTurn
from app.features.conversations.chats import CHAT_SCOPES, conversation_busy
from app.features.conversations.chats import checked_lesson_ids as checked_lesson_ids
from app.features.conversations.chats import cited_study_material as cited_study_material
from app.features.conversations.chats import preferred_chat as preferred_chat
from app.features.conversations.chats import require_chat as require_chat
from app.features.conversations.feynman_schemas import FeynmanData
from app.features.conversations.lesson_context import lesson_material, lesson_version, ready_lesson
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.schemas import (
    MAX_TITLE,
    ConversationMessageIn,
    ConversationOut,
    ConversationQuestionIn,
    ConversationStarted,
    ConversationTurnOut,
    ConversationUsage,
    LessonConversationOut,
)
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.mcp.recorder import ACTIVE

__all__ = ["ConversationOut", "ConversationQuestionIn", "ConversationStarted"]

LESSON_SCOPE = "lesson"
TRAINING_SCOPE: Final = "training"
BRAIN_SCOPE: Final = "brain"
THREAD_TOKEN_LIMIT = 100_000
DAY_TOKEN_LIMIT = 300_000
TURN_LIMIT = 100


async def _usage(repo: TurnRepository, thread_id: str) -> tuple[ConversationUsage, int]:
    zone = user_zone((await SettingsService(repo.session, repo.user_id).get()).timezone)
    day_start = local_moment(local_today(zone), "00:00", zone)
    thread, day, turns, reserved = await repo.usage(thread_id, day_start, TURN_TOKEN_LIMIT)
    return ConversationUsage(
        thread_tokens=thread,
        thread_token_limit=THREAD_TOKEN_LIMIT,
        day_tokens=day,
        day_token_limit=DAY_TOKEN_LIMIT,
        turns=turns,
        turn_limit=TURN_LIMIT,
    ), reserved


class _RepeatedRequest(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


@dataclass(frozen=True)
class ConversationThread:
    id: str
    scope: str
    subject_id: str
    graph: str = CONVERSATION_GRAPH

    @classmethod
    def for_subject(
        cls, user_id: str, scope: str, subject_id: str, *, graph: str = CONVERSATION_GRAPH
    ) -> "ConversationThread":
        # Deux premières soumissions concurrentes réservent le même fil dans prepare.
        key = uuid5(NAMESPACE_URL, f"tremplin/conversations/{user_id}/{scope}/{subject_id}")
        return cls(str(key), scope, subject_id, graph)


@dataclass(frozen=True)
class TurnOptions:
    lesson_version: str | None = None
    mode: str | None = None
    feynman: FeynmanData | None = None
    lesson_ids: list[str] | None = None


type PrepareTurn = Callable[[AsyncSession], Awaitable[TurnOptions]]


def _passage(message: ConversationQuestionIn) -> tuple[str | None, int | None]:
    if isinstance(message, ConversationMessageIn):
        return message.passage, message.passage_occurrence
    return None, None


def _same_request(previous: ConversationTurn, message: ConversationQuestionIn) -> str:
    passage, occurrence = _passage(message)
    if (previous.question, previous.passage, previous.passage_occurrence, previous.strong) != (
        message.question,
        passage,
        occurrence,
        message.strong,
    ):
        raise AppError(
            "conversation_request_conflict",
            "L'identifiant de cette demande a déjà servi pour un autre message.",
            409,
        )
    return previous.session_id


async def _check_limits(repo: TurnRepository, thread_id: str) -> None:
    await require_idle_conversation(repo.session, repo.user_id, thread_id)
    usage, reserved = await _usage(repo, thread_id)
    if usage.turns >= usage.turn_limit:
        scope = "turns"
    elif usage.thread_tokens + TURN_TOKEN_LIMIT > usage.thread_token_limit:
        scope = "thread"
    elif usage.day_tokens + reserved + TURN_TOKEN_LIMIT > usage.day_token_limit:
        scope = "day"
    else:
        return
    raise AppError(
        "conversation_budget_reached",
        "Le budget de conversation est atteint.",
        429,
        {"scope": scope},
    )


async def require_idle_conversation(db: AsyncSession, user_id: str, thread_id: str) -> None:
    turns = await TurnRepository(db, user_id).turns(thread_id)
    if any(status in OPEN_SESSION_STATES for _, status in turns):
        raise conversation_busy()


async def cancel_conversation_turn(db: AsyncSession, user_id: str, thread_id: str) -> str | None:
    return await TurnRepository(db, user_id).cancel_open(thread_id)


async def read_lesson_conversation(
    db: AsyncSession, user_id: str, lesson_id: str
) -> LessonConversationOut | None:
    await ready_lesson(db, user_id, lesson_id)
    thread_id = ConversationThread.for_subject(user_id, LESSON_SCOPE, lesson_id).id
    thread = await read_conversation(db, user_id, thread_id)
    if thread is None:
        return None
    return LessonConversationOut.model_validate({**thread.model_dump(), "lesson_id": lesson_id})


async def read_conversation(
    db: AsyncSession, user_id: str, thread_id: str
) -> ConversationOut | None:
    thread = await ConversationRepository(db, user_id).get(thread_id)
    if thread is None:
        return None
    repo = TurnRepository(db, user_id)
    turns = [
        ConversationTurnOut.model_validate(
            {
                name: status if name == "status" else getattr(row, name)
                for name in ConversationTurnOut.model_fields
            }
        )
        for row, status in await repo.turns(thread_id)
    ]
    usage, _ = await _usage(repo, thread_id)
    return ConversationOut.model_validate({"id": thread.id, "turns": turns, "usage": usage})


async def ensure_conversation(
    db: AsyncSession, user_id: str, thread: ConversationThread
) -> Conversation:
    repo = ConversationRepository(db, user_id)
    row = await repo.get(thread.id)
    if row is None:
        return await repo.add(id=thread.id, scope=thread.scope, subject_id=thread.subject_id)
    return row


def _reserve(
    user_id: str,
    thread: ConversationThread,
    turn_id: str,
    message: ConversationQuestionIn,
    authorize: PrepareTurn,
) -> PrepareSession:
    async def prepare(db: AsyncSession, session_id: str) -> None:
        turns = TurnRepository(db, user_id)
        request_id = str(message.request_id)
        if previous := await turns.by_request(thread.id, request_id):
            raise _RepeatedRequest(_same_request(previous, message))
        options = await authorize(db)
        await _check_limits(turns, thread.id)
        row = await ensure_conversation(db, user_id, thread)
        passage, occurrence = _passage(message)
        recorder = ACTIVE.get()
        turn = await turns.add(
            id=turn_id,
            thread_id=thread.id,
            request_id=request_id,
            session_id=session_id,
            question=message.question,
            passage=passage,
            passage_occurrence=occurrence,
            lesson_version=options.lesson_version,
            mode=options.mode,
            lesson_ids=options.lesson_ids,
            feynman=options.feynman.model_dump(mode="json") if options.feynman else None,
            strong=message.strong,
            mcp_call_id=recorder.call_id if recorder is not None else None,
        )
        if row.scope in CHAT_SCOPES:
            row.updated_at = turn.created_at
            if row.title is None:
                row.title = " ".join(message.question.split())[:MAX_TITLE]
        if recorder is not None:
            await recorder.persist_in(db)

    return prepare


async def ask_lesson_professor(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    lesson_id: str,
    message: ConversationMessageIn,
) -> ConversationStarted:
    await ready_lesson(db, user_id, lesson_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        _, markdown = await ready_lesson(tx, user_id, lesson_id)
        if message.passage is None:
            return TurnOptions()
        lesson_material(markdown, message.passage, message.passage_occurrence)
        return TurnOptions(lesson_version=lesson_version(markdown))

    thread = ConversationThread.for_subject(user_id, LESSON_SCOPE, lesson_id)
    return await submit_turn(runner, db, user_id, thread, message, authorize)


async def submit_turn(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    thread: ConversationThread,
    message: ConversationQuestionIn,
    authorize: PrepareTurn,
) -> ConversationStarted:
    if previous := await TurnRepository(db, user_id).by_request(thread.id, str(message.request_id)):
        sid = _same_request(previous, message)
        return await _replayed_start(db, user_id, sid, thread.graph)
    turn_id = new_id()
    try:
        sid = await runner.start(
            user_id,
            thread.graph,
            {"thread_id": thread.id, "turn_id": turn_id, "feynman": thread.scope in FEYNMAN_SCOPES},
            subject_type=thread.scope,
            subject_id=thread.subject_id,
            prepare=_reserve(user_id, thread, turn_id, message, authorize),
        )
    except _RepeatedRequest as repeated:
        return await _replayed_start(db, user_id, repeated.session_id, thread.graph)
    return ConversationStarted.model_validate({"session_id": sid})


async def _replayed_start(
    db: AsyncSession, user_id: str, sid: str, graph: str
) -> ConversationStarted:
    """Rend le même lancement au MCP joué, si la session appartient bien à ce client."""
    play = PLAY_CONTEXT.get()
    if play is not None and play.user_id == user_id and play.graph == graph:
        facts = await session_facts(db, user_id, sid)
        if facts is not None and play.client is not None and facts.played_by == play.client:
            play.started.append(sid)
    return ConversationStarted.model_validate({"session_id": sid})


async def claim_turn_reply(
    db: AsyncSession, user_id: str, thread_id: str, turn_id: str, session_id: str
) -> ConversationTurn | None:
    return await TurnRepository(db, user_id).claim_reply(thread_id, turn_id, session_id)
