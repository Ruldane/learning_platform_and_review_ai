from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.db.base import Base, new_id
from app.db.engine import create_engine, create_session_factory


@pytest.fixture
async def db_factory(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Fabrique de sessions sur un fichier SQLite isolé (schéma créé par `create_all`)."""
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'agents.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
def user_id() -> str:
    return new_id()


@pytest.fixture
def other_user_id() -> str:
    return new_id()
