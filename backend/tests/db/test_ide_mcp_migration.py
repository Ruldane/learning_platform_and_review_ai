"""Migration 0016 (10.P) : les dix tables de l'IDE et du MCP, leurs contraintes, retour arrière."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-17 10:00:00'"
TOKEN = (
    "INSERT INTO mcp_tokens (id, user_id, created_at, updated_at, label, hash, features, mode,"
    " expires_at) VALUES (:id, :user, "
    + NOW
    + ", "
    + NOW
    + ", 'Claude Code', :hash, '[]', 'read', "
    + NOW
    + ")"
)
NEW_TABLES = {
    "ide_exercises",
    "ide_sessions",
    "ide_runs",
    "ide_notes",
    "ide_preferences",
    "mcp_tokens",
    "mcp_prefs",
    "mcp_calls",
    "mcp_changes",
    "mcp_confirmations",
}


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _check_columns(inspector: Inspector) -> None:
    """Durable : séance réussie, signature d'erreur, refus sans jeton, entrées de 200 signes."""
    columns = {
        table: {str(c["name"]): c for c in inspector.get_columns(table)}
        for table in ("ide_sessions", "ide_runs", "ide_exercises", "mcp_calls")
    }
    assert columns["ide_sessions"]["passed_at"]["nullable"] is True
    assert columns["ide_runs"]["error_signature"]["nullable"] is True
    assert columns["ide_runs"]["error_signature"]["type"].length == 40
    assert columns["mcp_calls"]["token_id"]["nullable"] is True
    assert columns["mcp_calls"]["level"]["nullable"] is False
    for table in ("ide_sessions", "ide_runs", "ide_exercises"):
        assert columns[table]["entry"]["type"].length == 200, table


def test_migration_creates_and_drops_the_phase10_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0015")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        assert not NEW_TABLES & set(inspect(engine).get_table_names())
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= NEW_TABLES
        for table in NEW_TABLES:
            indexes = {str(i["name"]) for i in inspector.get_indexes(table)}
            assert f"ix_{table}_user_id" in indexes, table

        _check_columns(inspector)
        with engine.begin() as conn:
            conn.execute(text(TOKEN), {"id": "t1", "user": "u1", "hash": "a" * 64})
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(TOKEN), {"id": "t2", "user": "u2", "hash": "a" * 64})

        command.downgrade(cfg, "0015")
        assert not NEW_TABLES & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
