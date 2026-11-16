"""Migration 0013 (8.1) : tables du quotidien (projets, relevés du radar, briefs, registre des
passages), unicités, index, retour arrière."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
DAILY_TABLES = {"projects", "radar_runs", "briefs", "jobs"}
NOW = "'2026-11-16 08:00:00'"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _url(db_file: Path) -> str:
    return f"sqlite:///{db_file.as_posix()}"


def _tables(db_file: Path) -> set[str]:
    engine = create_sync_engine(_url(db_file))
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _columns(db_file: Path, table: str) -> dict[str, str]:
    engine = create_sync_engine(_url(db_file))
    try:
        return {str(c["name"]): str(c["type"]) for c in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


def _indexes(db_file: Path, table: str) -> dict[str, list[str]]:
    engine = create_sync_engine(_url(db_file))
    try:
        return {
            str(i["name"]): [str(c) for c in i["column_names"]]
            for i in inspect(engine).get_indexes(table)
        }
    finally:
        engine.dispose()


def _uniques(db_file: Path, table: str) -> dict[str, list[str]]:
    engine = create_sync_engine(_url(db_file))
    try:
        return {
            str(u["name"]): [str(c) for c in u["column_names"]]
            for u in inspect(engine).get_unique_constraints(table)
        }
    finally:
        engine.dispose()


def test_migration_creates_daily_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0012")
    assert not DAILY_TABLES & _tables(db_file)

    command.upgrade(cfg, "head")
    assert _tables(db_file) >= DAILY_TABLES
    assert _uniques(db_file, "projects") == {"uq_projects_user_id": ["user_id", "module_id"]}
    assert _uniques(db_file, "briefs") == {"uq_briefs_user_id": ["user_id", "day"]}
    assert _uniques(db_file, "jobs") == {"uq_jobs_user_id": ["user_id", "name", "period"]}
    assert _uniques(db_file, "radar_runs") == {}
    assert _indexes(db_file, "radar_runs")["ix_radar_runs_user_created"] == [
        "user_id",
        "created_at",
    ]
    assert _indexes(db_file, "jobs")["ix_jobs_user_name_started"] == [
        "user_id",
        "name",
        "started_at",
    ]
    for table in DAILY_TABLES:
        assert f"ix_{table}_user_id" in _indexes(db_file, table)
    assert "VARCHAR(40)" in _columns(db_file, "jobs")["name"]
    assert "VARCHAR(120)" in _columns(db_file, "radar_runs")["role_norm"]
    assert "VARCHAR(200)" in _columns(db_file, "projects")["title"]

    command.downgrade(cfg, "0012")
    assert not DAILY_TABLES & _tables(db_file)


PROJECT = (
    "INSERT INTO projects (id, user_id, created_at, updated_at, module_id, program_id, title,"
    " status, brief_attempts, submissions, drafts) VALUES (:id, :user, " + NOW + ", " + NOW + ","
    " :module, 'p1', 'Mini projet', 'brief_pending', 0, '[]', '{}')"
)
BRIEF = (
    "INSERT INTO briefs (id, user_id, created_at, updated_at, day, origin, sections, offer_keys,"
    " advice_status) VALUES (:id, :user, " + NOW + ", " + NOW + ", :day, 'opening', '{}', '[]',"
    " 'pending')"
)
JOB = (
    "INSERT INTO jobs (id, user_id, created_at, updated_at, name, period, status, started_at,"
    " attempts) VALUES (:id, :user, "
    + NOW
    + ", "
    + NOW
    + ", :name, :period, 'running', "
    + NOW
    + ", 1)"
)


def test_unique_constraints_are_per_user(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    engine = create_sync_engine(_url(db_file))
    try:
        with engine.begin() as conn:
            conn.execute(text(PROJECT), {"id": "x1", "user": "u1", "module": "m1"})
            conn.execute(text(PROJECT), {"id": "x2", "user": "u2", "module": "m1"})
            conn.execute(text(BRIEF), {"id": "b1", "user": "u1", "day": "2026-11-16"})
            conn.execute(text(BRIEF), {"id": "b2", "user": "u1", "day": "2026-11-17"})
            conn.execute(
                text(JOB), {"id": "j1", "user": "u1", "name": "daily_brief", "period": "d"}
            )
            conn.execute(
                text(JOB), {"id": "j2", "user": "u1", "name": "market_radar", "period": "d"}
            )
        for statement, params in (
            (PROJECT, {"id": "x3", "user": "u1", "module": "m1"}),
            (BRIEF, {"id": "b3", "user": "u1", "day": "2026-11-16"}),
            (JOB, {"id": "j3", "user": "u1", "name": "daily_brief", "period": "d"}),
        ):
            with pytest.raises(IntegrityError), engine.begin() as conn:
                conn.execute(text(statement), params)
    finally:
        engine.dispose()


def test_migration_0014_adds_the_radar_error_code(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0013")
    assert "error_code" not in _columns(db_file, "radar_runs")
    command.upgrade(cfg, "head")
    assert "error_code" in _columns(db_file, "radar_runs")
    command.downgrade(cfg, "0013")
    assert "error_code" not in _columns(db_file, "radar_runs")
    assert "radar_runs" in _tables(db_file)
