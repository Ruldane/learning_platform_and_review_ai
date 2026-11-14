"""Migration 0010 (6.10) : `cv_templates.prepared` et `cv_templates.pass_log` (CV d'origine
préparé et passes rendues d'un gabarit, D126)."""

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
        return {str(c["name"]) for c in inspect(engine).get_columns("cv_templates")}
    finally:
        engine.dispose()


def test_migration_0010_adds_prepared_and_pass_log(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0009")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:  # un gabarit d'avant la migration
            conn.execute(
                text(
                    "INSERT INTO cv_templates (id, user_id, document_id, name, status, active,"
                    " fonts, font_gaps, passes, page_count, page_size, original_pages,"
                    " render_pages, selectable, created_at, updated_at) VALUES ('t1', 'u1', 'd1',"
                    " 'Modèle', 'ready', 0, '[]', '[]', 1, 1, '{}', '[]', '[]', 1,"
                    " '2026-11-14 08:00:00', '2026-11-14 08:00:00')"
                )
            )
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            row = conn.execute(text("SELECT prepared, pass_log FROM cv_templates")).one()
            assert tuple(row) == (None, "[]")
    finally:
        engine.dispose()
    assert {"prepared", "pass_log"} <= _columns(db_file)

    command.downgrade(cfg, "0009")
    assert not {"prepared", "pass_log"} & _columns(db_file)
