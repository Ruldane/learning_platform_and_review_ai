from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine

BUSY_TIMEOUT_MS = 5000


def _set_sqlite_pragmas(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # A writer that finds the database locked waits up to 5 s instead of failing
        # (« database is locked »): the event bus and the runner write at the same time.
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def create_engine(url: str) -> AsyncEngine:
    """Async engine; each SQLite connection switches to WAL, foreign keys are enabled and
    a lock timeout is set (`BUSY_TIMEOUT_MS`); SQL parameters are hidden in errors."""
    # hide_parameters: a SQL error never quotes its parameters (content, file name,
    # link), even in the trace of the generic error handler (spec 17.2).
    engine = _create_async_engine(url, hide_parameters=True)
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: the objects stay readable after the end-of-request commit.
    return async_sessionmaker(engine, expire_on_commit=False)
