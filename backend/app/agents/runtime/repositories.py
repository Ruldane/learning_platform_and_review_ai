from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import AgentSession, LlmCall, SessionEventRecord
from app.db.repository import UserScopedRepository


class SessionRepository(UserScopedRepository[AgentSession]):
    model = AgentSession

    async def add_usage(
        self, session_id: str, *, tokens_in: int, tokens_out: int, cost_usd: float
    ) -> tuple[int, int, float] | None:
        """Ajoute une consommation aux cumuls de la session et renvoie les nouveaux cumuls
        `(tokens_in, tokens_out, cost_usd)`, `None` si elle n'existe pas pour cet utilisateur.

        Un seul `UPDATE` relatif : deux appels concurrents ne s'écrasent pas.
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


class EventRepository(UserScopedRepository[SessionEventRecord]):
    model = SessionEventRecord

    async def list_after(
        self, session_id: str, after_seq: int, limit: int | None = None
    ) -> list[SessionEventRecord]:
        """Événements de la session dont `seq` dépasse `after_seq`, par `seq` croissant
        (au plus `limit` s'il est donné : le rejeu lit par lots)."""
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
