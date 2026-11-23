"""Migration 0074 : étape et justification des semaines, pages officielles et API anciennes."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-23 08:00:00'"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _insert(conn: object, sql: str) -> None:
    conn.execute(text(sql))  # type: ignore[attr-defined]


def test_migration_0074_adds_the_columns_with_empty_defaults(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0073")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _insert(
                conn,
                "INSERT INTO goals (id, user_id, created_at, updated_at, text, framing, status)"
                f" VALUES ('g1', 'u1', {NOW}, {NOW}, 'But', '{{}}', 'chosen')",
            )
            _insert(
                conn,
                "INSERT INTO programs (id, user_id, created_at, updated_at, goal_id, title,"
                " version, status, start_date, weekly_minutes, cap_minutes) VALUES"
                f" ('p1', 'u1', {NOW}, {NOW}, 'g1', 'P', 1, 'draft', '2026-11-23', 840, 714)",
            )
            _insert(
                conn,
                "INSERT INTO weeks (id, user_id, created_at, updated_at, program_id, rank, theme,"
                f" objective, deliverable, start_date) VALUES ('w1', 'u1', {NOW}, {NOW}, 'p1', 1,"
                " 'Bases', 'Savoir', 'Un dépôt', '2026-11-23')",
            )
            _insert(
                conn,
                "INSERT INTO modules (id, user_id, created_at, updated_at, week_id, program_id,"
                f" rank, title, skills, prerequisites, skipped) VALUES ('m1', 'u1', {NOW}, {NOW},"
                " 'w1', 'p1', 0, 'Module', '[]', '[]', 0)",
            )
        command.upgrade(cfg, "0074")
        with engine.connect() as conn:
            week = conn.execute(text("SELECT stage, rationale FROM weeks")).one()
            module = conn.execute(text("SELECT official_urls, legacy FROM modules")).one()
        assert tuple(week) == (None, None)
        assert tuple(module) == ("[]", "[]")
        names = {c["name"] for c in inspect(engine).get_columns("weeks")}
        assert {"stage", "rationale"} <= names
    finally:
        engine.dispose()
    command.downgrade(cfg, "0073")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        assert "stage" not in {c["name"] for c in inspect(engine).get_columns("weeks")}
        assert "legacy" not in {c["name"] for c in inspect(engine).get_columns("modules")}
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM modules")).scalar_one() == 1
    finally:
        engine.dispose()
