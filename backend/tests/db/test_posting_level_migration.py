"""Existing postings keep their content when their seniority codes change."""

import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
POSTING_TEXT = "Offre d'une équipe à Lyon."
ANALYSIS = {
    "title": "Développeuse confirmée",
    "requirements": [{"text": "Expérience confirmée", "skills": ["Python"]}],
    "remote": "inconnu",
}


def _seed(engine: Engine) -> None:
    with engine.begin() as connection:
        for posting_id, level, owner in (
            ("mid", "confirme", "u1"),
            ("unknown", "inconnu", "u2"),
            ("senior", "senior", "u1"),
            ("unanalysed", None, "u2"),
        ):
            connection.execute(
                text(
                    "INSERT INTO job_postings (id, user_id, created_at, updated_at, source, "
                    "text, text_hash, status, analysis, duplicates, distinct_from) "
                    "VALUES (:id, :owner, '2026-11-24', '2026-11-24', 'text', "
                    ":text, :id, 'ready', :analysis, '[]', '[]')"
                ),
                {
                    "id": posting_id,
                    "owner": owner,
                    "text": POSTING_TEXT,
                    "analysis": json.dumps({**ANALYSIS, "level": level}) if level else None,
                },
            )


def _postings(engine: Engine) -> dict[str, dict[str, object]]:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id, user_id, updated_at, text, analysis FROM job_postings")
        )
        return {
            row.id: dict(row._mapping)
            | {"analysis": json.loads(row.analysis) if row.analysis is not None else None}
            for row in result
        }


def test_posting_level_migration_changes_only_the_codes(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(config, "0076")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        _seed(engine)
        before = _postings(engine)
        command.upgrade(config, "0077")
        assert _postings(engine) == before | {
            "mid": before["mid"] | {"analysis": ANALYSIS | {"level": "mid_level"}},
            "unknown": before["unknown"] | {"analysis": ANALYSIS | {"level": "unknown"}},
        }
        command.downgrade(config, "0076")
        assert _postings(engine) == before
    finally:
        engine.dispose()
