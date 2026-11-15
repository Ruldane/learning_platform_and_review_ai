"""Migration 0011 (7.1) : tables des candidatures, index des relances, dossier d'entreprise,
source `interview` des fiches de révision, cascades, retour arrière."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Connection, inspect, text
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
APPLICATION_TABLES = {
    "applications",
    "application_events",
    "contacts",
    "reminders",
    "kit_items",
    "interviews",
    "committee_runs",
}
NOW = "'2026-11-15 08:00:00'"


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


def _index_columns(db_file: Path, table: str) -> dict[str, list[str]]:
    engine = create_sync_engine(_url(db_file))
    try:
        return {
            str(i["name"]): [str(c) for c in i["column_names"]]
            for i in inspect(engine).get_indexes(table)
        }
    finally:
        engine.dispose()


def _application(conn: Connection, app_id: str = "a1") -> None:
    conn.execute(
        text(
            "INSERT INTO applications (id, user_id, created_at, updated_at, company, company_norm,"
            " title, status, distinct_from) VALUES (:id, 'u1', " + NOW + ", " + NOW + ","
            " 'Société Fictive', 'societe fictive', 'Développeuse IA', 'to_apply', '[]')"
        ),
        {"id": app_id},
    )


def test_migration_creates_tables_and_widens_card_source(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0010")
    assert not APPLICATION_TABLES & _tables(db_file)
    engine = create_sync_engine(_url(db_file))
    try:
        with engine.begin() as conn:  # une fiche de révision d'avant la migration
            conn.execute(
                text(
                    "INSERT INTO flashcards (id, user_id, created_at, updated_at, front, back,"
                    " front_hash, source, step, due_date) VALUES ('c0', 'u1', "
                    + NOW
                    + ", "
                    + NOW
                    + ", 'Q', 'R', 'h0', 'quiz', 0, '2026-11-16')"
                )
            )
        command.upgrade(cfg, "head")
        assert _tables(db_file) >= APPLICATION_TABLES
        assert _index_columns(db_file, "reminders")["ix_reminders_due_on_status"] == [
            "due_on",
            "status",
        ]
        assert {"dossier", "dossier_sources", "dossier_at"} <= set(_columns(db_file, "companies"))
        assert "VARCHAR(16)" in _columns(db_file, "flashcards")["source"]
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO flashcards (id, user_id, created_at, updated_at, front, back,"
                    " front_hash, source, step, due_date) VALUES ('c1', 'u1', "
                    + NOW
                    + ", "
                    + NOW
                    + ", 'Q2', 'R2', 'h1', 'interview', 0, '2026-11-16')"
                )
            )
            sources = conn.execute(text("SELECT source FROM flashcards ORDER BY id")).all()
            assert [row[0] for row in sources] == ["quiz", "interview"]
        # La contrainte d'unicité et l'index des fiches survivent à la reconstruction de table.
        assert "ix_flashcards_user_due" in _index_columns(db_file, "flashcards")
    finally:
        engine.dispose()

    command.downgrade(cfg, "0010")
    assert not APPLICATION_TABLES & _tables(db_file)
    assert not {"dossier", "dossier_sources", "dossier_at"} & set(_columns(db_file, "companies"))
    assert "VARCHAR(8)" in _columns(db_file, "flashcards")["source"]


def test_children_cascade_and_reminders_are_unique_per_anchor(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "head")
    engine = create_sync_engine(_url(db_file))
    reminder = (
        "INSERT INTO reminders (id, user_id, created_at, updated_at, application_id, kind,"
        " anchor_on, due_on, status) VALUES (:id, 'u1', " + NOW + ", " + NOW + ", 'a1',"
        " 'linkedin_7', '2026-11-01', '2026-11-08', 'pending')"
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
            _application(conn)
            conn.execute(text(reminder), {"id": "r1"})
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(reminder), {"id": "r2"})  # même type, même ancre
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.execute(text("DELETE FROM applications WHERE id = 'a1'"))
            assert conn.execute(text("SELECT count(*) FROM reminders")).scalar_one() == 0
    finally:
        engine.dispose()
