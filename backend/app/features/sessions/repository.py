import builtins
from collections.abc import Collection

from sqlalchemy import func, select

from app.db.models.agents import AgentSession, SessionEventRecord
from app.db.repository import UserScopedRepository

OPEN_STATUSES = ("running", "waiting_user", "paused")


class SessionReadRepository(UserScopedRepository[AgentSession]):
    """Session reads for the API (writes go through the runner)."""

    model = AgentSession

    async def list_recent(
        self, *, graph: str | None, status: str | None
    ) -> builtins.list[AgentSession]:
        """The user's sessions, most recent first, filtered if requested."""
        stmt = select(AgentSession).where(AgentSession.user_id == self.user_id)
        if graph is not None:
            stmt = stmt.where(AgentSession.graph == graph)
        if status is not None:
            stmt = stmt.where(AgentSession.status == status)
        stmt = stmt.order_by(AgentSession.created_at.desc(), AgentSession.id.desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def latest_open(self, *, graph: str, subject_type: str, subject_id: str) -> str | None:
        """Identifier of the most recent open session (`OPEN_STATUSES`) of `graph` on this
        subject, `None` if there is none."""
        return await self.latest(
            graph=graph, subject_type=subject_type, subject_id=subject_id, statuses=OPEN_STATUSES
        )

    async def open_ids(
        self, *, graph: str, subject_type: str, subject_id: str
    ) -> builtins.list[str]:
        """Identifiers of ALL open sessions of `graph` on this subject."""
        stmt = select(AgentSession.id).where(
            AgentSession.user_id == self.user_id,
            AgentSession.graph == graph,
            AgentSession.subject_type == subject_type,
            AgentSession.subject_id == subject_id,
            AgentSession.status.in_(OPEN_STATUSES),
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_ids_by_subject(
        self, *, graph: str, subject_type: str
    ) -> builtins.dict[str, builtins.list[str]]:
        """The user's open sessions of `graph`, grouped by subject (`subject_id`): a single
        query for all subjects of one type."""
        stmt = select(AgentSession.subject_id, AgentSession.id).where(
            AgentSession.user_id == self.user_id,
            AgentSession.graph == graph,
            AgentSession.subject_type == subject_type,
            AgentSession.subject_id.is_not(None),
            AgentSession.status.in_(OPEN_STATUSES),
        )
        out: builtins.dict[str, builtins.list[str]] = {}
        for subject_id, session_id in (await self.session.execute(stmt)).all():
            if subject_id is not None:
                out.setdefault(subject_id, []).append(session_id)
        return out

    async def latest(
        self,
        *,
        graph: str,
        subject_type: str,
        subject_id: str,
        statuses: Collection[str] | None = None,
    ) -> str | None:
        """Identifier of the most recent session of `graph` on this subject (among `statuses`
        if given), `None` if there is none."""
        stmt = select(AgentSession.id).where(
            AgentSession.user_id == self.user_id,
            AgentSession.graph == graph,
            AgentSession.subject_type == subject_type,
            AgentSession.subject_id == subject_id,
        )
        if statuses is not None:
            stmt = stmt.where(AgentSession.status.in_(builtins.list(statuses)))
        stmt = stmt.order_by(AgentSession.created_at.desc(), AgentSession.id.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def last_seqs(self, session_ids: Collection[str]) -> dict[str, int]:
        """Last `seq` written for each session (missing from the result: no event)."""
        if not session_ids:
            return {}
        stmt = (
            select(SessionEventRecord.session_id, func.max(SessionEventRecord.seq))
            .where(
                SessionEventRecord.user_id == self.user_id,
                SessionEventRecord.session_id.in_(builtins.list(session_ids)),
            )
            .group_by(SessionEventRecord.session_id)
        )
        return {sid: int(seq) for sid, seq in (await self.session.execute(stmt)).all()}
