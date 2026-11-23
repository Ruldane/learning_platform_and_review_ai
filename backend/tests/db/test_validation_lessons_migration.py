"""Migration 0076 : retire les leçons des modules « Valider mes acquis » (D309)."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-23 08:00:00'"
ROW = "user_id, created_at, updated_at"
VALUES = f"'u1', {NOW}, {NOW}"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _seed(conn: object) -> None:
    rows = [
        f"INSERT INTO goals (id, {ROW}, text, framing, status)"
        f" VALUES ('g1', {VALUES}, 'But', '{{}}', 'chosen')",
        f"INSERT INTO programs (id, {ROW}, goal_id, title, version, status, start_date,"
        f" weekly_minutes, cap_minutes) VALUES ('p1', {VALUES}, 'g1', 'P', 1, 'validated',"
        " '2026-11-23', 840, 714)",
        f"INSERT INTO weeks (id, {ROW}, program_id, rank, theme, objective, deliverable,"
        f" start_date) VALUES ('w1', {VALUES}, 'p1', 1, 'Bases', 'Savoir', 'Un dépôt',"
        " '2026-11-23')",
    ]
    for rank, (module_id, kind) in enumerate((("m1", "NULL"), ("m2", "'validation'"))):
        rows.append(
            f"INSERT INTO modules (id, {ROW}, week_id, program_id, rank, title, skills,"
            f" prerequisites, skipped, kind) VALUES ('{module_id}', {VALUES}, 'w1', 'p1', {rank},"
            f" 'Module', '[]', '[]', 0, {kind})"
        )
        rows.append(
            f"INSERT INTO lessons (id, {ROW}, module_id, program_id, title, markdown,"
            f" word_count, status, attempts) VALUES ('l-{module_id}', {VALUES}, '{module_id}',"
            " 'p1', 'Leçon', '# Leçon', 2, 'ready', 1)"
        )
        rows.append(
            f"INSERT INTO resources (id, {ROW}, module_id, program_id, type, title, url,"
            f" url_hash, reason, status) VALUES ('r-{module_id}', {VALUES}, '{module_id}', 'p1',"
            " 'article', 'Doc', 'https://example.com', 'h', '', 'to_read')"
        )
    for sql in rows:
        conn.execute(text(sql))  # type: ignore[attr-defined]


def test_migration_0076_drops_only_validation_module_lessons(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0075")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
        command.upgrade(cfg, "0076")
        with engine.connect() as conn:
            lessons = set(conn.execute(text("SELECT id FROM lessons")).scalars())
            resources = set(conn.execute(text("SELECT id FROM resources")).scalars())
            modules = conn.execute(text("SELECT count(*) FROM modules")).scalar_one()
        assert lessons == {"l-m1"}
        assert resources == {"r-m1"}
        assert modules == 2  # le module de validation garde son quiz
    finally:
        engine.dispose()
