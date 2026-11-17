"""Quelles tables partent dans l'export : toutes celles qui ont `user_id`, lues dans
`Base.metadata`, sauf les sessions de connexion ; et la forme JSON d'une ligne."""

from datetime import UTC, date, datetime, timedelta, timezone

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.db.base import Base
from app.features.account.service.tables import (
    exported_columns,
    row_json,
    user_tables,
)


def test_user_tables_include_every_scoped_table() -> None:
    names = {table.name for table in user_tables()}
    assert {"users", "user_settings", "api_keys", "llm_calls", "goals", "memory_items"} <= names
    for table in Base.metadata.tables.values():
        if "user_id" in table.c and table.info.get("export", True):
            assert table.name in names


def test_user_tables_leave_out_the_login_sessions_and_unscoped_tables() -> None:
    names = {table.name for table in user_tables()}
    assert "auth_sessions" not in names
    assert all("user_id" in table.c for table in user_tables())


def test_user_tables_follow_the_dependency_order() -> None:
    order = [table.name for table in user_tables()]
    assert order == [t.name for t in Base.metadata.sorted_tables if t.name in order]


def test_api_keys_never_export_the_encrypted_key() -> None:
    table = Base.metadata.tables["api_keys"]
    names = [column.name for column in exported_columns(table)]
    assert "encrypted_key" not in names and {"provider", "last4", "user_id"} <= set(names)
    assert [c.name for c in exported_columns(Base.metadata.tables["goals"])] == [
        c.name for c in Base.metadata.tables["goals"].c
    ]


def test_row_json_writes_dates_in_iso_and_keeps_json_as_is() -> None:
    row = {
        "at": datetime(2026, 11, 17, 9, 30, tzinfo=UTC),
        "local": datetime(2026, 11, 17, 10, 30, tzinfo=timezone(timedelta(hours=1))),
        "day": date(2026, 11, 17),
        "data": {"a": [1, 2, {"b": None}], "c": "é"},
        "n": 3,
        "flag": True,
        "none": None,
        "text": "bonjour",
    }
    assert row_json(row) == {
        "at": "2026-11-17T09:30:00+00:00",
        "local": "2026-11-17T10:30:00+01:00",
        "day": "2026-11-17",
        "data": {"a": [1, 2, {"b": None}], "c": "é"},
        "n": 3,
        "flag": True,
        "none": None,
        "text": "bonjour",
    }
