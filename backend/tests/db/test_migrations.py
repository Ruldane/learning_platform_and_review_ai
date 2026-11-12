from pathlib import Path
from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect, text

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from alembic import command
from app.db.base import Base
from app.db.engine import create_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    # Les tables des tests (préfixe `test_`) ne font pas partie du schéma migré.
    return not (type_ == "table" and name is not None and name.startswith("test_"))


def test_migrations_match_models(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "head")

    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"include_object": _include_object, "compare_type": True}
        )
        diff = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    assert diff == []


async def test_wal_mode_is_enabled(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'wal.db').as_posix()}")
    try:
        async with engine.connect() as conn:
            mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar_one()
            fk = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
            busy = (await conn.execute(text("PRAGMA busy_timeout"))).scalar_one()
    finally:
        await engine.dispose()
    assert mode == "wal"
    assert fk == 1
    assert busy == 5000  # écrivains concurrents (bus d'événements) : attendre, pas échouer


RESEARCH_TABLES = {"web_cache", "sources", "web_queries", "search_usage"}
RESEARCH_UNIQUES = {
    "web_cache": ("uq_web_cache_user_id", ["user_id", "kind", "key_hash"]),
    "sources": ("uq_sources_user_id", ["user_id", "session_id", "url_hash"]),
    "web_queries": ("uq_web_queries_user_id", ["user_id", "session_id", "query_hash"]),
    "search_usage": (
        "uq_search_usage_user_id",
        ["user_id", "provider", "month", "key_fingerprint"],
    ),
}


def test_migration_0004_creates_research_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    sync_url = f"sqlite:///{db_file.as_posix()}"

    def inspected() -> tuple[set[str], dict[str, Any]]:
        engine = create_sync_engine(sync_url)
        try:
            insp = inspect(engine)
            uniques = {
                t: insp.get_unique_constraints(t) for t in RESEARCH_TABLES if insp.has_table(t)
            }
            indexes = (
                {i["name"] for i in insp.get_indexes("sources")}
                if insp.has_table("sources")
                else set()
            )
            return set(insp.get_table_names()), {"uniques": uniques, "indexes": indexes}
        finally:
            engine.dispose()

    command.upgrade(cfg, "head")
    tables, found = inspected()
    assert tables >= RESEARCH_TABLES
    for table, (name, columns) in RESEARCH_UNIQUES.items():
        assert {"name": name, "column_names": columns} in found["uniques"][table]
    assert {"ix_sources_user_session", "ix_sources_user_id"} <= found["indexes"]

    command.downgrade(cfg, "0003")  # ne retire que les tables de la recherche
    tables, _ = inspected()
    assert not RESEARCH_TABLES & tables and {"memory_items", "sessions"} <= tables
    command.upgrade(cfg, "head")
    assert inspected()[0] >= RESEARCH_TABLES
