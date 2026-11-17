"""Migration 0015 (9.P) : table `auth_sessions` (jeton haché unique, index sur `user_id`) et
réglages déjà stockés marqués « premier lancement fait » ; retour arrière."""

import json
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-17 08:00:00'"
SETTINGS = (
    "INSERT INTO user_settings (id, user_id, created_at, updated_at, data) VALUES (:id, :user, "
    + NOW
    + ", "
    + NOW
    + ", :data)"
)
SESSION = (
    "INSERT INTO auth_sessions (id, user_id, created_at, updated_at, token_hash, expires_at)"
    " VALUES (:id, :user, " + NOW + ", " + NOW + ", :hash, " + NOW + ")"
)


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _url(db_file: Path) -> str:
    return f"sqlite:///{db_file.as_posix()}"


def test_migration_creates_auth_sessions(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0014")
    engine = create_sync_engine(_url(db_file))
    try:
        assert "auth_sessions" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        assert "auth_sessions" in inspector.get_table_names()
        columns = {str(c["name"]): str(c["type"]) for c in inspector.get_columns("auth_sessions")}
        assert "VARCHAR(64)" in columns["token_hash"] and "expires_at" in columns
        uniques = {
            str(u["name"]): [str(c) for c in u["column_names"]]
            for u in inspector.get_unique_constraints("auth_sessions")
        }
        assert uniques == {"uq_auth_sessions_token_hash": ["token_hash"]}
        indexes = {
            str(i["name"]): [str(c) for c in i["column_names"]]
            for i in inspector.get_indexes("auth_sessions")
        }
        assert indexes == {"ix_auth_sessions_user_id": ["user_id"]}

        with engine.begin() as conn:
            conn.execute(text(SESSION), {"id": "s1", "user": "u1", "hash": "a" * 64})
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(SESSION), {"id": "s2", "user": "u2", "hash": "a" * 64})

        command.downgrade(cfg, "0014")
        assert "auth_sessions" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_migration_marks_existing_settings_onboarded(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0014")
    engine = create_sync_engine(_url(db_file))
    try:
        with engine.begin() as conn:
            conn.execute(
                text(SETTINGS), {"id": "r1", "user": "u1", "data": '{"brief_time": "06:30"}'}
            )
            conn.execute(text(SETTINGS), {"id": "r2", "user": "u2", "data": "{}"})
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT user_id, data FROM user_settings ORDER BY id")).all()
        stored = {user: json.loads(data) for user, data in rows}
        assert stored["u1"] == {"brief_time": "06:30", "onboarding_done": True}
        assert stored["u2"] == {"onboarding_done": True}

        command.downgrade(cfg, "0014")  # le drapeau reste, sans effet
        with engine.connect() as conn:
            data = conn.execute(text("SELECT data FROM user_settings WHERE id = 'r2'")).scalar_one()
        assert json.loads(data) == {"onboarding_done": True}
    finally:
        engine.dispose()
