"""Migration 0009 (6.8) : `documents.tags` (étiquettes d'un document rangé par une feature,
D124)."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _columns(db_file: Path) -> set[str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return {str(c["name"]) for c in inspect(engine).get_columns("documents")}
    finally:
        engine.dispose()


def test_migration_0009_adds_document_tags(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0008")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:  # un document d'avant la migration
            conn.execute(
                text(
                    "INSERT INTO documents (id, user_id, name, source_kind, status, source_hash,"
                    " learned, created_at, updated_at) VALUES ('d1', 'u1', 'Doc', 'pdf', 'queued',"
                    " 'h', 0, '2026-11-14 08:00:00', '2026-11-14 08:00:00')"
                )
            )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT tags FROM documents")).scalar_one() == "[]"
    finally:
        engine.dispose()
    assert "tags" in _columns(db_file)

    command.downgrade(cfg, "0008")
    assert "tags" not in _columns(db_file)
