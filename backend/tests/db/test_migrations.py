from pathlib import Path
from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import text

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from alembic import command
from app.db.base import Base
from app.db.engine import create_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    # Les tables des tests (préfixe `test_`) ne font pas partie du schéma migré.
    return not (type_ == "table" and name is not None and name.startswith("test_"))


def test_migrations_match_models(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "head")

    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"include_object": _include_object, "compare_type": True}
        )
        diff = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    assert diff == []


async def test_wal_mode_is_enabled(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'wal.db').as_posix()}")
    try:
        async with engine.connect() as conn:
            mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar_one()
            fk = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
    finally:
        await engine.dispose()
    assert mode == "wal"
    assert fk == 1
