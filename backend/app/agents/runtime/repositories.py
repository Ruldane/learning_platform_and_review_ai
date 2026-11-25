from collections.abc import Collection
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import AgentSession, LlmCall, SessionEventRecord
from app.db.repository import UserScopedRepository


class SessionRepository(UserScopedRepository[AgentSession]):
    model = AgentSession

    async def add_usage(
        self, session_id: str, *, tokens_in: int, tokens_out: int, cost_usd: float
    ) -> tuple[int, int, float] | None:
        """Adds a consumption to the session's totals and returns the new totals
        `(tokens_in, tokens_out, cost_usd)`, `None` if it does not exist for this user.

        A single relative `UPDATE`: two concurrent calls do not overwrite each other.
        """
        stmt = (
            update(AgentSession)
            .where(AgentSession.id == session_id, AgentSession.user_id == self.user_id)
            .values(
                tokens_in=AgentSession.tokens_in + tokens_in,
                tokens_out=AgentSession.tokens_out + tokens_out,
                cost_usd=AgentSession.cost_usd + cost_usd,
            )
            .returning(AgentSession.tokens_in, AgentSession.tokens_out, AgentSession.cost_usd)
            .execution_options(synchronize_session=False)
        )
        row = (await self.session.execute(stmt)).first()
        return None if row is None else (row[0], row[1], row[2])

    async def open_ids(self, statuses: Collection[str]) -> list[str]:
        """IDs of the user's sessions whose status is in `statuses`, in
        creation order."""
        stmt = (
            select(AgentSession.id)
            .where(AgentSession.user_id == self.user_id, AgentSession.status.in_(list(statuses)))
            .order_by(AgentSession.created_at, AgentSession.id)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def transition(
        self, session_id: str, *, from_: Collection[str], to: str, **values: Any
    ) -> bool:
        """Sets the session to status `to` (writing `values`) only if its status is
        in `from_`; `True` if done. A single conditional `UPDATE`: of two concurrent
        transitions (double click, pause during the end of the graph), only one wins."""
        stmt = (
            update(AgentSession)
            .where(
                AgentSession.id == session_id,
                AgentSession.user_id == self.user_id,
                AgentSession.status.in_(list(from_)),
            )
            .values(status=to, **values)
            .returning(AgentSession.id)
            .execution_options(synchronize_session=False)
        )
        return (await self.session.execute(stmt)).first() is not None


class EventRepository(UserScopedRepository[SessionEventRecord]):
    model = SessionEventRecord

    async def list_after(
        self, session_id: str, after_seq: int, limit: int | None = None
    ) -> list[SessionEventRecord]:
        """Session events whose `seq` exceeds `after_seq`, by increasing `seq`
        (at most `limit` if given: replay reads in batches)."""
        stmt = (
            select(SessionEventRecord)
            .where(
                SessionEventRecord.user_id == self.user_id,
                SessionEventRecord.session_id == session_id,
                SessionEventRecord.seq > after_seq,
            )
            .order_by(SessionEventRecord.seq)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def max_seq(self, session_id: str) -> int:
        """Highest `seq` of the session, 0 if it has no event."""
        stmt = select(func.coalesce(func.max(SessionEventRecord.seq), 0)).where(
            SessionEventRecord.user_id == self.user_id,
            SessionEventRecord.session_id == session_id,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def last_seq_of(self, session_id: str, types: Collection[str]) -> int | None:
        """`seq` of the last event of one of these types, `None` if there is none."""
        stmt = select(func.max(SessionEventRecord.seq)).where(
            SessionEventRecord.user_id == self.user_id,
            SessionEventRecord.session_id == session_id,
            SessionEventRecord.type.in_(list(types)),
        )
        seq = (await self.session.execute(stmt)).scalar_one()
        return None if seq is None else int(seq)


class LlmCallRepository(UserScopedRepository[LlmCall]):
    model = LlmCall

    async def usage_of_session(self, session_id: str) -> tuple[str | None, int]:
        """`(model of the last call, input + output tokens)` of the session: what the journal
        of a teacher call says (never a text). `(None, 0)` without a logged call."""
        stmt = (
            select(LlmCall.model, LlmCall.tokens_in + LlmCall.tokens_out)
            .where(LlmCall.user_id == self.user_id, LlmCall.session_id == session_id)
            .order_by(LlmCall.created_at, LlmCall.id)
        )
        rows = (await self.session.execute(stmt)).all()
        return (rows[-1][0] if rows else None), sum(int(row[1]) for row in rows)


async def list_sessions_to_recover(db: AsyncSession) -> list[tuple[str, str]]:
    """`(user_id, session_id)` of the `running` sessions, all users included.

    The project's only query that does not filter by `user_id`: it is reserved for server startup,
    when the runner resumes the sessions interrupted by a stop. Never
    call it from a user's request.
    """
    stmt = select(AgentSession.user_id, AgentSession.id).where(AgentSession.status == "running")
    return [(user_id, session_id) for user_id, session_id in (await db.execute(stmt)).all()]
