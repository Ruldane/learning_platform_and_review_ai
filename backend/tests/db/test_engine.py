"""Le moteur SQLite (D181, point 3) : l'`ERROR sqlalchemy.pool … Exception terminating connection`
vu deux fois sur la pile jetable de la phase 8 n'a pas été reproduit ; ces scénarios (tâche annulée
pendant une écriture bloquée ou une longue série d'écritures, moteur fermé pendant une écriture)
gardent ce qui est établi : une connexion rendue ou annulée proprement ne journalise rien."""

import asyncio
import gc
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.engine import create_engine, create_session_factory

type Scenario = Callable[[AsyncEngine, async_sessionmaker[AsyncSession]], Awaitable[None]]


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(f"{record.levelname} {record.name}")


async def _cancelled(task: asyncio.Task[None]) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def _writer_blocked_then_cancelled(
    engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
) -> None:
    holder = factory()
    await holder.execute(text("insert into t values (1)"))  # tient le verrou d'écriture

    async def blocked() -> None:
        async with factory() as db:
            await db.execute(text("insert into t values (2)"))
            await db.commit()

    task = asyncio.create_task(blocked())
    await asyncio.sleep(0.3)
    await _cancelled(task)
    await holder.rollback()
    await holder.close()


async def _many_writes_then_cancelled(
    engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
) -> None:
    async def many() -> None:
        async with factory() as db:
            for rank in range(2_000):
                await db.execute(text("insert into t values (:rank)"), {"rank": rank})
            await db.commit()

    task = asyncio.create_task(many())
    await asyncio.sleep(0.2)
    await _cancelled(task)


async def _dispose_during_writes(
    engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
) -> None:
    async def many() -> None:
        async with factory() as db:
            for rank in range(5_000):
                await db.execute(text("insert into t values (:rank)"), {"rank": rank})
            await db.commit()

    task = asyncio.create_task(many())
    await asyncio.sleep(0.2)
    await engine.dispose()
    await _cancelled(task)


@pytest.mark.parametrize(
    "scenario",
    [_writer_blocked_then_cancelled, _many_writes_then_cancelled, _dispose_during_writes],
)
async def test_engine_cancelled_sessions_then_dispose_log_no_pool_error(
    tmp_path: Path, scenario: Scenario
) -> None:
    records = _Records()
    pool_logger = logging.getLogger("sqlalchemy.pool")
    pool_logger.addHandler(records)
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}")
    try:
        factory = create_session_factory(engine)
        async with factory() as db:
            await db.execute(text("create table t (x integer)"))
            await db.commit()
        await scenario(engine, factory)
        await engine.dispose()
        gc.collect()
        await asyncio.sleep(0.2)
    finally:
        pool_logger.removeHandler(records)
    assert records.messages == []
