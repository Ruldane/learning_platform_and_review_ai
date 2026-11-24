"""Model tiers keep their selected models and MCP undo history across the rename."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, create_engine, select

from alembic import command
from app.db.models.accounts import UserSettingsRow
from app.db.models.mcp import McpChange

FAST_MODEL = {"provider": "glm", "model": "preferred-fast-model"}
STRONG_MODEL = {"provider": "anthropic", "model": "preferred-strong-model"}
STANDARD_MODEL = {"provider": "openai", "model": "preferred-standard-model"}
BEFORE = {"rapide": FAST_MODEL, "standard": STANDARD_MODEL, "fort": STRONG_MODEL}
AFTER = {"fast": FAST_MODEL, "standard": STANDARD_MODEL, "strong": STRONG_MODEL}
PREFERENCES = {"style_guide": "Un ton rapide et fort.", "onboarding_done": True}


def _seed(conn: Connection) -> None:
    settings = UserSettingsRow.__table__
    conn.execute(
        settings.insert(),
        [
            {"id": "settings", "user_id": "u1", "data": {**PREFERENCES, "tiers": BEFORE}},
            {"id": "unset", "user_id": "u2", "data": {}},
        ],
    )
    conn.execute(
        McpChange.__table__.insert().values(
            id="change",
            user_id="u1",
            call_id="call",
            table_name="user_settings",
            row_id="settings",
            op="update",
            before={"data": {"tiers": BEFORE}},
            after={"data": {**PREFERENCES, "tiers": BEFORE}},
        )
    )


def _assert_tiers(conn: Connection, tiers: dict[str, dict[str, str]]) -> None:
    settings = select(UserSettingsRow.data).order_by(UserSettingsRow.id)
    expected = {**PREFERENCES, "tiers": tiers}
    assert conn.execute(settings).scalars().all() == [expected, {}]
    changes = select(McpChange.before, McpChange.after)
    assert conn.execute(changes).one() == ({"data": {"tiers": tiers}}, {"data": expected})


def test_model_tier_rename_preserves_preferences_and_undo(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(config, "0087")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
        command.upgrade(config, "0088")
        with engine.connect() as conn:
            _assert_tiers(conn, AFTER)
        command.downgrade(config, "0087")
        with engine.connect() as conn:
            _assert_tiers(conn, BEFORE)
    finally:
        engine.dispose()
