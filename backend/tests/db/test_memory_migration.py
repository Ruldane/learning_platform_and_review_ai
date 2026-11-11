from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
MEMORY_TABLES = {"documents", "memory_items", "memory_chunks", "memory_writes"}


def _tables(url: str) -> set[str]:
    engine = create_sync_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_memory_migration_upgrades_downgrades_and_upgrades_again(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    sync_url = f"sqlite:///{db_file.as_posix()}"

    command.upgrade(cfg, "head")
    assert _tables(sync_url) >= MEMORY_TABLES
    command.downgrade(cfg, "0002")
    after = _tables(sync_url)
    assert not (MEMORY_TABLES & after) and {"sessions", "llm_calls"} <= after
    command.upgrade(cfg, "head")
    assert _tables(sync_url) >= MEMORY_TABLES
