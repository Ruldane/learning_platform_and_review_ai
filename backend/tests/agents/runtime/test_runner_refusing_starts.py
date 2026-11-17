"""Garde par compte de `SessionRunner` : pendant « Tout supprimer », aucune session ne démarre ni
ne reprend pour ce compte, et les autres comptes ne sont pas touchés."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.runner import ACCOUNT_DELETING_CODE, SessionRunner
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from tests.agents.runtime.runner_helpers import wait_idle, wait_status

type Factory = async_sessionmaker[AsyncSession]


async def _count(db_factory: Factory, user_id: str) -> int:
    async with db_factory() as db:
        stmt = select(func.count()).select_from(AgentSession).where(AgentSession.user_id == user_id)
        return int((await db.execute(stmt)).scalar_one())


async def test_start_is_refused_while_the_account_is_being_deleted(
    runner: SessionRunner, db_factory: Factory, user_id: str
) -> None:
    async with runner.refusing_starts(user_id):
        with pytest.raises(AppError) as refused:
            await runner.start(user_id, "two_steps", {})
    assert refused.value.code == ACCOUNT_DELETING_CODE and refused.value.status_code == 409
    assert await _count(db_factory, user_id) == 0  # aucune ligne écrite


async def test_resume_is_refused_while_the_account_is_being_deleted(
    runner: SessionRunner, db_factory: Factory, user_id: str
) -> None:
    sid = await runner.start(user_id, "ask", {})
    await wait_status(db_factory, user_id, sid, "waiting_user")
    await wait_idle(runner, sid)
    async with runner.refusing_starts(user_id):
        with pytest.raises(AppError) as refused:
            await runner.resume(user_id, sid, None, "oui")
    assert refused.value.code == ACCOUNT_DELETING_CODE


async def test_the_guard_is_per_account_and_lifted_afterwards(
    runner: SessionRunner, db_factory: Factory, user_id: str, other_user_id: str
) -> None:
    async with runner.refusing_starts(user_id):
        other = await runner.start(other_user_id, "two_steps", {})
        await wait_status(db_factory, other_user_id, other, "completed")
    after = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, after, "completed")


async def test_the_guard_is_lifted_when_the_deletion_fails(
    runner: SessionRunner, user_id: str
) -> None:
    with pytest.raises(RuntimeError):
        async with runner.refusing_starts(user_id):
            raise RuntimeError("panne")
    sid = await runner.start(user_id, "two_steps", {})
    assert sid


async def test_open_sessions_lists_the_open_ones_of_the_account_only(
    runner: SessionRunner, db_factory: Factory, user_id: str, other_user_id: str
) -> None:
    waiting = await runner.start(user_id, "ask", {})
    await wait_status(db_factory, user_id, waiting, "waiting_user")
    done = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, done, "completed")
    foreign = await runner.start(other_user_id, "ask", {})
    await wait_status(db_factory, other_user_id, foreign, "waiting_user")

    assert await runner.open_sessions(user_id) == [waiting]
    assert await runner.open_sessions(other_user_id) == [foreign]
