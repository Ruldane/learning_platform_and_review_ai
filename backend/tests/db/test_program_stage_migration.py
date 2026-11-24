"""Migrations for program stages, scheduled tasks and their history."""

import json
from datetime import date
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy import create_engine as create_sync_engine

from alembic import command
from app.db.models.mcp import McpChange
from app.db.models.program import Module, PlanVersion, Task

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-23 08:00:00'"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _insert(conn: Connection, sql: str) -> None:
    conn.execute(text(sql))


def _seed_week(conn: Connection) -> None:
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


def test_migration_0074_adds_the_columns_with_empty_defaults(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0073")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed_week(conn)
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


def _stages(engine: Engine) -> tuple[str, str, str, str]:
    with engine.connect() as conn:
        stage, rationale = conn.execute(
            text("SELECT stage, rationale FROM weeks WHERE id='w1'")
        ).one()
        before, after = conn.execute(
            text('SELECT "before", "after" FROM mcp_changes WHERE id = :id'), {"id": "change1"}
        ).one()
        return stage, rationale, json.loads(before)["stage"], json.loads(after)["stage"]


def test_program_stage_codes_preserve_the_rationale_and_undo(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0082")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed_week(conn)
            conn.execute(text("UPDATE weeks SET stage='avance', rationale='Étape finale.'"))
            conn.execute(
                text(
                    "INSERT INTO mcp_changes (id, user_id, created_at, updated_at, call_id, "
                    'table_name, row_id, op, "before", "after") VALUES '
                    f"('change1', 'u1', {NOW}, {NOW}, 'call1', 'weeks', 'w1', 'update', "
                    ":before, :after)"
                ),
                {
                    "before": json.dumps({"stage": "pratique"}),
                    "after": json.dumps({"stage": "avance"}),
                },
            )
        original = _stages(engine)
        command.upgrade(cfg, "0083")
        assert _stages(engine) == ("advanced", "Étape finale.", "practice", "advanced")
        command.downgrade(cfg, "0082")
        assert _stages(engine) == original
    finally:
        engine.dispose()


TASKS_BEFORE = [
    {"type": "lire", "title": "Lire la leçon"},
    {"type": "regarder", "title": "Regarder la vidéo"},
    {"type": "pratiquer", "title": "Pratiquer le tri"},
    {"type": "quiz", "title": "Quiz"},
    {"type": "projet", "title": "Projet personnel"},
]
TASKS_AFTER = [
    {"type": "read", "title": "Lire la leçon"},
    {"type": "watch", "title": "Regarder la vidéo"},
    {"type": "practice", "title": "Pratiquer le tri"},
    {"type": "quiz", "title": "Quiz"},
    {"type": "project", "title": "Projet personnel"},
]


def _plan_snapshot(tasks: list[dict[str, str]]) -> dict[str, object]:
    return {"weeks": [{"modules": [{"title": "Mon cours", "tasks": tasks}]}]}


def _seed_task_rows(conn: Connection) -> dict[str, object]:
    _seed_week(conn)
    module = Module.__table__.insert()
    task = Task.__table__.insert()
    version = PlanVersion.__table__.insert()
    conn.execute(
        module,
        {
            "id": "m1",
            "user_id": "u1",
            "week_id": "w1",
            "program_id": "p1",
            "rank": 1,
            "title": "Mon cours",
        },
    )
    conn.execute(
        task,
        {
            "id": "t1",
            "user_id": "u1",
            "module_id": "m1",
            "program_id": "p1",
            "rank": 1,
            "minutes": 15,
            "done_criterion": "Lire la leçon.",
            "planned_date": date(2026, 11, 23),
            **TASKS_BEFORE[0],
        },
    )
    snapshot = _plan_snapshot(TASKS_BEFORE)
    conn.execute(
        version,
        {"id": "v1", "user_id": "u1", "program_id": "p1", "version": 1, "snapshot": snapshot},
    )
    return snapshot


def _seed_task_codes(conn: Connection) -> None:
    snapshot = _seed_task_rows(conn)
    for table, row, content in (
        ("tasks", "t1", TASKS_BEFORE[0]),
        ("plan_versions", "v1", {"snapshot": snapshot}),
    ):
        conn.execute(
            McpChange.__table__.insert(),
            {
                "id": table,
                "user_id": "u1",
                "call_id": "call",
                "table_name": table,
                "row_id": row,
                "op": "update",
                "before": content,
                "after": content,
            },
        )


def _task_states(engine: Engine) -> tuple[dict[str, object], object, list[tuple[object, ...]]]:
    with engine.connect() as conn:
        task = conn.execute(text("SELECT type, title FROM tasks")).mappings().one()
        version = conn.execute(text("SELECT snapshot FROM plan_versions")).scalar_one()
        entries = conn.execute(
            text('SELECT table_name, "before", "after" FROM mcp_changes ORDER BY table_name')
        )
        return (
            dict(task),
            json.loads(version),
            [(table, json.loads(before), json.loads(after)) for table, before, after in entries],
        )


def test_task_code_migration_preserves_versions_and_undo_history(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0083")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed_task_codes(conn)
        before = _task_states(engine)
        command.upgrade(cfg, "0084")
        snapshot = _plan_snapshot(TASKS_AFTER)
        version = {"snapshot": snapshot}
        assert _task_states(engine) == (
            TASKS_AFTER[0],
            snapshot,
            [("plan_versions", version, version), ("tasks", TASKS_AFTER[0], TASKS_AFTER[0])],
        )
        command.downgrade(cfg, "0083")
        assert _task_states(engine) == before
    finally:
        engine.dispose()
