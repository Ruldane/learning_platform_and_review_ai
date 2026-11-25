"""Renaming radar seniority preserves the order and contents of existing scan results."""

import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[2]
OFFER = {"ref": "p1", "title": "Ingénieure confirmée", "remote": "inconnu", "skills": []}
UNREAD = {"ref": "p4", "read": "blocked"}


def _create_scan(engine: Engine, postings: list[dict[str, object]]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO radar_runs (id, user_id, created_at, updated_at, role, zone, "
                "role_norm, zone_norm, trigger, status, queries, candidates, read_count, "
                "blocked_count, not_postings, analyzed, blocked_domains, postings, ranking, "
                "alerts) VALUES ('r1', 'u1', '2026-11-24', '2026-11-24', 'Ingénieure IA', "
                "'Lyon', 'ingenieure ia', 'lyon', 'manual', 'done', 1, 4, 3, 1, 0, 3, "
                "'{}', :postings, '[]', '[]')"
            ),
            {"postings": json.dumps(postings, ensure_ascii=False)},
        )


def _scan(engine: Engine) -> tuple[str, str, str, list[dict[str, object]]]:
    with engine.connect() as connection:
        user, role, updated, postings = connection.execute(
            text("SELECT user_id, role, updated_at, postings FROM radar_runs WHERE id = 'r1'")
        ).one()
    return user, role, updated, json.loads(postings)


def test_radar_migration_preserves_the_saved_scan(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(config, "0078")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    first = OFFER | {"level": "confirme"}
    second = OFFER | {"ref": "p2", "level": "inconnu"}
    third = OFFER | {"ref": "p3", "level": "senior"}
    try:
        _create_scan(engine, [first, second, third, UNREAD])
        before = _scan(engine)
        command.upgrade(config, "0079")
        assert _scan(engine) == (
            "u1",
            "Ingénieure IA",
            "2026-11-24",
            [first | {"level": "mid_level"}, second | {"level": "unknown"}, third, UNREAD],
        )
        command.downgrade(config, "0078")
        assert _scan(engine) == before
    finally:
        engine.dispose()
