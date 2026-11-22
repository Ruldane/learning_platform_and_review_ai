"""Lectures au nom du compte des seuls tours de la porte Débat."""

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.expert_debate_port import EXPERT_SCOPE
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.conversations import Conversation, ConversationTurn


class DebateRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self.db, self.user_id = db, user_id

    def _owned(self) -> Select[ConversationTurn, AgentSession]:
        user = self.user_id
        return (
            select(ConversationTurn, AgentSession)
            .join(
                Conversation,
                and_(Conversation.id == ConversationTurn.thread_id, Conversation.user_id == user),
            )
            .join(
                AgentSession,
                and_(AgentSession.id == ConversationTurn.session_id, AgentSession.user_id == user),
            )
            .where(Conversation.scope == EXPERT_SCOPE, ConversationTurn.user_id == user)
        )

    async def recent(self) -> list[tuple[ConversationTurn, AgentSession]]:
        stmt = (
            self._owned()
            .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id)
            .limit(50)
        )
        return [(turn, session) for turn, session in await self.db.execute(stmt)]

    async def by_debate(self, debate_id: str) -> tuple[ConversationTurn, AgentSession]:
        stmt = self._owned().where(Conversation.subject_id == debate_id)
        return await self._require(stmt)

    async def by_run(
        self, thread_id: str, turn_id: str, session_id: str
    ) -> tuple[ConversationTurn, AgentSession]:
        stmt = self._owned().where(
            ConversationTurn.thread_id == thread_id,
            ConversationTurn.id == turn_id,
            ConversationTurn.session_id == session_id,
        )
        return await self._require(stmt)

    async def _require(
        self, stmt: Select[ConversationTurn, AgentSession]
    ) -> tuple[ConversationTurn, AgentSession]:
        result = (await self.db.execute(stmt)).one_or_none()
        if result is None:
            raise AppError("debate_not_found", "Débat introuvable.", 404)
        turn, session = result
        return turn, session
