"""Lancement dans un fil P11, lecture des sources et sauvegarde du jugement."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.runner import SessionRunner
from app.agents.tools.expert_debate_port import (
    EXPERT_GRAPH,
    EXPERT_SCOPE,
    ExpertDraft,
    ExpertSpeech,
)
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.conversations import ConversationTurn
from app.features.conversations.service import (
    ConversationQuestionIn,
    ConversationThread,
    TurnOptions,
    claim_turn_reply,
    submit_turn,
)
from app.features.expert_debates.repository import DebateRepository
from app.features.expert_debates.schemas import (
    ExpertDebateOut,
    ExpertDebateStarted,
    ExpertDebateSummary,
)


def _summary(turn: ConversationTurn, session: AgentSession) -> ExpertDebateSummary:
    return ExpertDebateSummary.model_validate(
        {
            "id": turn.request_id,
            "session_id": session.id,
            "question": turn.question,
            "status": session.status,
            "created_at": turn.created_at,
        }
    )


def _view(turn: ConversationTurn, session: AgentSession) -> ExpertDebateOut:
    return ExpertDebateOut.model_validate(
        {
            **_summary(turn, session).model_dump(),
            "speeches": turn.expert_speeches or [],
            "judgment": turn.expert_judgment,
        }
    )


async def start_debate(
    runner: SessionRunner, db: AsyncSession, user_id: str, message: ConversationQuestionIn
) -> ExpertDebateStarted:
    debate_id = message.request_id
    thread = ConversationThread.for_subject(
        user_id, EXPERT_SCOPE, str(debate_id), graph=EXPERT_GRAPH
    )

    async def authorize(_: AsyncSession) -> TurnOptions:
        return TurnOptions()

    started = await submit_turn(runner, db, user_id, thread, message, authorize)
    return ExpertDebateStarted(debate_id=debate_id, session_id=started.session_id)


class ExpertDebates:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._repo = DebateRepository(db, user_id)

    async def list(self) -> list[ExpertDebateSummary]:
        return [_summary(turn, session) for turn, session in await self._repo.recent()]

    async def read(self, debate_id: UUID) -> ExpertDebateOut:
        return _view(*(await self._repo.by_debate(str(debate_id))))

    async def judge(self, debate_id: UUID, text: str) -> ExpertDebateOut:
        turn, session = await self._repo.by_debate(str(debate_id))
        if session.status != "completed" or not turn.expert_speeches:
            raise AppError("debate_pending", "Attends la fin des prises de parole.", 409)
        turn.expert_judgment = text
        return _view(turn, session)


class AgentExpertDebates:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def draft(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ExpertDraft:
        async with self._factory() as db:
            turn, session = await DebateRepository(db, user_id).by_run(
                thread_id, turn_id, session_id
            )
            return ExpertDraft(
                turn.question,
                turn.strong,
                session.tokens_in + session.tokens_out,
                turn.expert_speeches is not None,
            )

    async def publish(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        speeches: Sequence[ExpertSpeech],
    ) -> None:
        async with self._factory() as db:
            await DebateRepository(db, user_id).by_run(thread_id, turn_id, session_id)
            turn = await claim_turn_reply(db, user_id, thread_id, turn_id, session_id)
            if turn is not None:
                turn.expert_speeches = [speech.model_dump(mode="json") for speech in speeches]
                turn.answer = "Débat terminé."
            await db.commit()
