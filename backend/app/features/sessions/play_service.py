"""Lecture d'un brief sous l'identité MCP et la portée métier du parcours."""

from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.features.sessions.play_schemas import PlayBrief
from app.features.sessions.repository import SessionReadRepository
from app.mcp.played import play_identity


async def owned_play(
    request: Request, db: AsyncSession, user_id: str, session_id: str, *, write: bool = False
) -> AgentSession:
    identity = play_identity(user_id, write=write)
    row = await SessionReadRepository(db, user_id).get(session_id)
    if row is None or row.played_by is None:
        raise AppError("session_not_found", "Session jouée introuvable.", 404)
    feature = request.app.state.mcp_registry.graph_features.get(row.graph)
    if feature not in identity.features:
        raise AppError("play_forbidden", "Ce parcours est hors de la portée du jeton.", 403)
    return row


def brief_view(row: AgentSession) -> PlayBrief:
    pending = row.pending_interrupt or {}
    brief = pending.get("brief") or {}
    return PlayBrief.model_validate(
        {
            "session_id": row.id,
            "status": row.status,
            "played_by": row.played_by,
            "expires_at": pending.get("expires_at"),
            **brief,
        }
    )


async def expire_steps(
    factory: async_sessionmaker[AsyncSession], now: datetime, *, user_id: str | None = None
) -> None:
    stmt = update(AgentSession).where(
        AgentSession.played_by.is_not(None),
        AgentSession.status == "waiting_user",
        AgentSession.pending_interrupt["expires_at"].as_string() <= now.astimezone(UTC).isoformat(),
    )
    if user_id is not None:
        stmt = stmt.where(AgentSession.user_id == user_id)
    async with factory() as db:
        await db.execute(stmt.values(status="expired", pending_interrupt=None, play_delivery=None))
        await db.commit()
