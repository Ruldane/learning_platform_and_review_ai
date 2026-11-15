"""Migration 0012 (7.3) : `reminders.postponed`, faux pour les relances existantes."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-15 08:00:00'"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def test_migration_0012_adds_postponed_false_by_default(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0011")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO applications (id, user_id, created_at, updated_at, company,"
                    " company_norm, title, status, distinct_from) VALUES ('a1', 'u1', "
                    + NOW
                    + ", "
                    + NOW
                    + ", 'Société Fictive', 'societe fictive', 'Poste',"
                    " 'applied', '[]')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO reminders (id, user_id, created_at, updated_at, application_id,"
                    " kind, anchor_on, due_on, status) VALUES ('r1', 'u1', "
                    + NOW
                    + ", "
                    + NOW
                    + ", 'a1', 'linkedin_7', '2026-11-01', '2026-11-08', 'pending')"
                )
            )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT postponed FROM reminders")).scalar_one() == 0
        assert "postponed" in {c["name"] for c in inspect(engine).get_columns("reminders")}
    finally:
        engine.dispose()
    command.downgrade(cfg, "0011")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        assert "postponed" not in {c["name"] for c in inspect(engine).get_columns("reminders")}
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM reminders")).scalar_one() == 1
    finally:
        engine.dispose()
