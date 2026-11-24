"""Lesson migrations preserve content and update resource codes."""

import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, Engine, text
from sqlalchemy import create_engine as create_sync_engine

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
NOW = "'2026-11-23 08:00:00'"
ROW = "user_id, created_at, updated_at"
VALUES = f"'u1', {NOW}, {NOW}"


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _seed(conn: Connection) -> None:
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
        conn.execute(text(sql))


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


LEGACY_RESOURCE = {"type": "depot", "level": "intermediaire", "note": "Dépôt à relire."}
CURRENT_RESOURCE = LEGACY_RESOURCE | {"type": "repository", "level": "intermediate"}
LEGACY_DRAFT = {
    "markdown": "# Une leçon à garder",
    "resources": [
        {"type": "cours", "level": "debutant", "title": "Le cours"},
        {"type": "papier", "level": "avance", "title": "Le papier"},
        {"type": "article", "level": None, "title": "Niveau inconnu"},
    ],
}
CURRENT_DRAFT = LEGACY_DRAFT | {
    "resources": [
        {"type": "course", "level": "beginner", "title": "Le cours"},
        {"type": "paper", "level": "advanced", "title": "Le papier"},
        {"type": "article", "level": None, "title": "Niveau inconnu"},
    ],
}


def _seed_resource_codes(conn: Connection) -> None:
    _seed(conn)
    conn.execute(
        text("UPDATE resources SET type=:type, level=:level, note=:note WHERE id='r-m1'"),
        LEGACY_RESOURCE,
    )
    conn.execute(
        text("UPDATE lessons SET verification_draft=:draft WHERE id='l-m1'"),
        {"draft": json.dumps(LEGACY_DRAFT, ensure_ascii=False)},
    )
    for table, row, snapshot in (
        ("resources", "r-m1", LEGACY_RESOURCE),
        ("lessons", "l-m1", {"verification_draft": LEGACY_DRAFT}),
    ):
        conn.execute(
            text(
                "INSERT INTO mcp_changes (id, user_id, created_at, updated_at, call_id, "
                'table_name, row_id, op, "before", "after") VALUES '
                "(:table, 'u1', '2026-11-24', '2026-11-24', 'call', :table, :row, "
                "'update', :snapshot, :snapshot)"
            ),
            {"table": table, "row": row, "snapshot": json.dumps(snapshot, ensure_ascii=False)},
        )


def _resource_states(engine: Engine) -> tuple[dict[str, object], object, list[tuple[object, ...]]]:
    with engine.connect() as conn:
        resource = (
            conn.execute(text("SELECT type, level, note FROM resources WHERE id = 'r-m1'"))
            .mappings()
            .one()
        )
        draft = conn.execute(
            text("SELECT verification_draft FROM lessons WHERE id = 'l-m1'")
        ).scalar_one()
        snapshots = conn.execute(
            text('SELECT table_name, "before", "after" FROM mcp_changes ORDER BY table_name')
        )
        return (
            dict(resource),
            json.loads(draft),
            [(table, json.loads(before), json.loads(after)) for table, before, after in snapshots],
        )


def test_resource_code_migration_preserves_drafts_and_undo_history(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "0081")
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed_resource_codes(conn)
        before = _resource_states(engine)
        command.upgrade(cfg, "0082")
        draft_snapshot = {"verification_draft": CURRENT_DRAFT}
        assert _resource_states(engine) == (
            CURRENT_RESOURCE,
            CURRENT_DRAFT,
            [
                ("lessons", draft_snapshot, draft_snapshot),
                ("resources", CURRENT_RESOURCE, CURRENT_RESOURCE),
            ],
        )
        command.downgrade(cfg, "0081")
        assert _resource_states(engine) == before
    finally:
        engine.dispose()
