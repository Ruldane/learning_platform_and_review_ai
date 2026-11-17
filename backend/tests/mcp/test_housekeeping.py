"""La tâche planifiée du MCP (10.B2) : demandes périmées expirées, vieux appels purgés."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpCall, McpConfirmation
from app.scheduler.base import JobContext
from app.scheduler.jobs import mcp_housekeeping

Factory = async_sessionmaker[AsyncSession]


async def test_housekeeping_job_expires_requests_and_purges_old_calls(
    db_session_factory: Factory,
) -> None:
    now = datetime.now(UTC)
    async with db_session_factory() as db:
        db.add(
            McpConfirmation(
                user_id="u1",
                token_id="t1",
                action="x",
                status="pending",
                expires_at=now - timedelta(minutes=5),
            )
        )
        for days in (45, 2):
            db.add(
                McpCall(
                    user_id="u1",
                    token_id="t1",
                    action="x",
                    level=1,
                    code=200,
                    created_at=now - timedelta(days=days),
                )
            )
        await db.commit()
    context = cast(JobContext, SimpleNamespace(session_factory=db_session_factory))

    await mcp_housekeeping.run(context)

    async with db_session_factory() as db:
        status = (await db.execute(select(McpConfirmation.status))).scalar_one()
        ages: list[Any] = list((await db.execute(select(McpCall.created_at))).scalars())
    assert status == "expired"
    assert len(ages) == 1 and ages[0] > now - timedelta(days=3)
