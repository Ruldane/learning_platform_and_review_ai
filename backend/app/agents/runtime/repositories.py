from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import AgentSession, LlmCall, SessionEventRecord
from app.db.repository import UserScopedRepository


class SessionRepository(UserScopedRepository[AgentSession]):
    model = AgentSession


class EventRepository(UserScopedRepository[SessionEventRecord]):
    model = SessionEventRecord

    async def list_after(self, session_id: str, after_seq: int) -> list[SessionEventRecord]:
        """Événements de la session dont `seq` dépasse `after_seq`, par `seq` croissant."""
        stmt = (
            select(SessionEventRecord)
            .where(
                SessionEventRecord.user_id == self.user_id,
                SessionEventRecord.session_id == session_id,
                SessionEventRecord.seq > after_seq,
            )
            .order_by(SessionEventRecord.seq)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def max_seq(self, session_id: str) -> int:
        """Plus grand `seq` de la session, 0 si elle n'a aucun événement."""
        stmt = select(func.coalesce(func.max(SessionEventRecord.seq), 0)).where(
            SessionEventRecord.user_id == self.user_id,
            SessionEventRecord.session_id == session_id,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class LlmCallRepository(UserScopedRepository[LlmCall]):
    model = LlmCall


async def list_sessions_to_recover(db: AsyncSession) -> list[tuple[str, str]]:
    """`(user_id, session_id)` des sessions `running`, tous utilisateurs confondus.

    Seule requête du projet qui ne filtre pas par `user_id` : elle est réservée au démarrage
    du serveur, quand le runner reprend les sessions interrompues par un arrêt. Ne jamais
    l'appeler depuis une requête d'un utilisateur.
    """
    stmt = select(AgentSession.user_id, AgentSession.id).where(AgentSession.status == "running")
    return [(user_id, session_id) for user_id, session_id in (await db.execute(stmt)).all()]
