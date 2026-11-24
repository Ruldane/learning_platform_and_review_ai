"""Undo snapshots stay comparable after translating stored codes."""

import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
POSTING_BEFORE = {"analysis": {"level": "inconnu", "title": "Niveau inconnu"}}
POSTING_AFTER = {"analysis": {"level": "confirme", "title": "Poste confirmé"}}
QUESTION_BEFORE = {"type": "qcm", "prompt": "Question de QCM", "correct_index": 0}
QUESTION_AFTER = QUESTION_BEFORE | {"correct_index": 2}


def _seed(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, before, after in (
            ("job_postings", POSTING_BEFORE, POSTING_AFTER),
            ("quiz_questions", QUESTION_BEFORE, QUESTION_AFTER),
            ("memory_items", QUESTION_BEFORE, None),
        ):
            conn.execute(
                text(
                    "INSERT INTO mcp_changes (id, user_id, created_at, updated_at, call_id, "
                    'table_name, row_id, op, "before", "after") VALUES '
                    "(:table, 'u1', '2026-11-24', '2026-11-24', 'call', :table, 'row', "
                    "'update', :before, :after)"
                ),
                {
                    "table": table,
                    "before": json.dumps(before),
                    "after": json.dumps(after) if after is not None else None,
                },
            )


def _snapshots(engine: Engine) -> dict[str, tuple[object, object]]:
    with engine.connect() as conn:
        rows = conn.execute(text('SELECT table_name, "before", "after" FROM mcp_changes'))
        return {
            table: (json.loads(before), json.loads(after) if after is not None else None)
            for table, before, after in rows
        }


def test_migrate_only_the_codes_in_old_undo_snapshots(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(config, "0080")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        _seed(engine)
        before = _snapshots(engine)
        command.upgrade(config, "0081")
        assert _snapshots(engine) == {
            "job_postings": (
                {"analysis": {"level": "unknown", "title": "Niveau inconnu"}},
                {"analysis": {"level": "mid_level", "title": "Poste confirmé"}},
            ),
            "quiz_questions": (
                QUESTION_BEFORE | {"type": "mcq"},
                QUESTION_AFTER | {"type": "mcq"},
            ),
            "memory_items": before["memory_items"],
        }
        command.downgrade(config, "0080")
        assert _snapshots(engine) == before
    finally:
        engine.dispose()
