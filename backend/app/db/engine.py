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
        # Un écrivain qui trouve la base verrouillée attend jusqu'à 5 s au lieu d'échouer
        # (« database is locked ») : le bus d'événements et le runner écrivent en même temps.
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def create_engine(url: str) -> AsyncEngine:
    """Moteur asynchrone ; chaque connexion SQLite passe en WAL, clés étrangères actives et
    délai d'attente sur verrou (`BUSY_TIMEOUT_MS`)."""
    engine = _create_async_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False : les objets restent lisibles après le commit de fin de requête.
    return async_sessionmaker(engine, expire_on_commit=False)
