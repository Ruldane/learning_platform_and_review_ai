"""Migration 0006 (5.2) : tables, index, rattrapage de `plan_versions.status`, retour arrière."""

from datetime import date
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
STUDY_TABLES = {
    "quizzes",
    "quiz_questions",
    "quiz_attempts",
    "flashcards",
    "study_sessions",
    "skill_snapshots",
    "journal_entries",
}
DAY = date(2026, 11, 12)


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _inspect(db_file: Path, call: str, *args: str) -> list[dict[str, object]]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        result: list[dict[str, object]] = getattr(inspect(engine), call)(*args)
        return result
    finally:
        engine.dispose()


def _tables(db_file: Path) -> set[str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _indexes(db_file: Path, table: str) -> dict[str, dict[str, object]]:
    return {str(i["name"]): i for i in _inspect(db_file, "get_indexes", table)}


def _columns(db_file: Path, table: str) -> set[str]:
    return {str(c["name"]) for c in _inspect(db_file, "get_columns", table)}


def test_migration_0006_creates_study_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    assert _tables(db_file) >= STUDY_TABLES
    assert "ix_flashcards_user_due" in _indexes(db_file, "flashcards")
    assert "uq_study_sessions_open" in _indexes(db_file, "study_sessions")
    assert "uq_quiz_attempts_grading" in _indexes(db_file, "quiz_attempts")
    assert "ix_quiz_attempts_user_quiz" in _indexes(db_file, "quiz_attempts")
    assert "ix_journal_entries_user_created" in _indexes(db_file, "journal_entries")
    assert "fail_streak" in _columns(db_file, "user_skills")
    assert {"kind", "status", "base_fingerprint", "review_entry_id", "week_loads"} <= _columns(
        db_file, "plan_versions"
    )


def test_migration_0006_partial_indexes_are_unique(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.connect() as conn:
            sql = {
                row[0]: row[1]
                for row in conn.execute(
                    text("SELECT name, sql FROM sqlite_master WHERE type = 'index'")
                )
            }
    finally:
        engine.dispose()
    assert "WHERE status = 'open'" in sql["uq_study_sessions_open"]
    assert "WHERE status = 'grading'" in sql["uq_quiz_attempts_grading"]
    assert sql["uq_study_sessions_open"].startswith("CREATE UNIQUE INDEX")
    assert sql["uq_quiz_attempts_grading"].startswith("CREATE UNIQUE INDEX")


def test_migration_0006_backfills_plan_version_status(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0005")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            for number, accepted in ((1, None), (2, "2026-11-10 08:00:00"), (3, None)):
                conn.execute(
                    text(
                        "INSERT INTO plan_versions (id, user_id, created_at, updated_at, "
                        "program_id, version, snapshot, reason, accepted_at) VALUES "
                        "(:id, 'u1', '2026-11-10 08:00:00', '2026-11-10 08:00:00', 'p1', "
                        ":version, '{}', '', :accepted)"
                    ),
                    {"id": f"v{number}", "version": number, "accepted": accepted},
                )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT version, status, kind FROM plan_versions ORDER BY version")
            ).all()
    finally:
        engine.dispose()
    assert [tuple(r) for r in rows] == [
        (1, "superseded", "build"),
        (2, "accepted", "build"),
        (3, "superseded", "build"),
    ]


def test_migration_0006_downgrade(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0005")
    assert not (STUDY_TABLES & _tables(db_file))
    assert "fail_streak" not in _columns(db_file, "user_skills")
    assert "status" not in _columns(db_file, "plan_versions")
    assert "accepted_at" in _columns(db_file, "plan_versions")
    command.upgrade(cfg, "head")
    assert _tables(db_file) >= STUDY_TABLES
