"""Migration 0007 (6.1) : `llm_calls.estimated` (tokens estimés d'un appel coupé, D117)."""

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
        return {str(c["name"]) for c in inspect(engine).get_columns("llm_calls")}
    finally:
        engine.dispose()


def test_migration_0007_adds_estimated(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0006")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:  # une ligne d'avant la migration
            conn.execute(
                text(
                    "INSERT INTO llm_calls (id, user_id, provider, model, tokens_in, tokens_out,"
                    " latency_ms, cost_usd, created_at, updated_at) VALUES ('c1', 'u1', 'glm',"
                    " 'm', 1, 2, 3, 0.0, '2026-11-13 10:00:00', '2026-11-13 10:00:00')"
                )
            )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT estimated FROM llm_calls")).scalar_one() == 0
    finally:
        engine.dispose()
    assert "estimated" in _columns(db_file)

    command.downgrade(cfg, "0006")
    assert "estimated" not in _columns(db_file)
