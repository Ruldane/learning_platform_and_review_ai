import builtins
from collections.abc import Collection

from sqlalchemy import func, select

from app.db.models.agents import AgentSession, SessionEventRecord
from app.db.repository import UserScopedRepository

OPEN_STATUSES = ("running", "waiting_user", "paused")


class SessionReadRepository(UserScopedRepository[AgentSession]):
    """Lectures des sessions pour l'API (les écritures passent par le runner)."""

    model = AgentSession

    async def list_recent(
        self, *, graph: str | None, status: str | None
    ) -> builtins.list[AgentSession]:
        """Sessions de l'utilisateur, les plus récentes d'abord, filtrées si demandé."""
        stmt = select(AgentSession).where(AgentSession.user_id == self.user_id)
        if graph is not None:
            stmt = stmt.where(AgentSession.graph == graph)
        if status is not None:
            stmt = stmt.where(AgentSession.status == status)
        stmt = stmt.order_by(AgentSession.created_at.desc(), AgentSession.id.desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def latest_open(self, *, graph: str, subject_type: str, subject_id: str) -> str | None:
        """Identifiant de la session ouverte (`OPEN_STATUSES`) la plus récente de `graph` sur
        cet objet, `None` s'il n'y en a pas."""
        return await self.latest(
            graph=graph, subject_type=subject_type, subject_id=subject_id, statuses=OPEN_STATUSES
        )

    async def open_ids(
        self, *, graph: str, subject_type: str, subject_id: str
    ) -> builtins.list[str]:
        """Identifiants de TOUTES les sessions ouvertes de `graph` sur cet objet."""
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
        """Sessions ouvertes de `graph` de l'utilisateur, rangées par objet (`subject_id`) : une
        seule requête pour tous les objets d'un type."""
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
        """Identifiant de la session la plus récente de `graph` sur cet objet (parmi `statuses`
        si donnés), `None` s'il n'y en a pas."""
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
        """Dernier `seq` écrit de chaque session (absente du résultat : aucun événement)."""
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
