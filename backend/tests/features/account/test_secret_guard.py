"""Une colonne ou une table secrète ne sort jamais dans l'export, et une colonne dont le nom
évoque un secret force une décision : la marquer `export: False` dans le modèle, ou la déclarer
relue dans `REVIEWED_NOT_SECRET`."""

from sqlalchemy import Column, MetaData, String, Table, Text

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.db.base import Base
from app.features.account.service.tables import (
    REVIEWED_NOT_SECRET,
    exported_columns,
    unreviewed_secret_columns,
    user_tables,
)


def _table(metadata: MetaData, name: str, *extra: Column[str], **info: bool) -> Table:
    id_, user_id = Column("id", String(36), primary_key=True), Column("user_id", String(36))
    return Table(name, metadata, id_, user_id, *extra, info=info)


def test_every_secret_looking_column_of_the_application_is_decided() -> None:
    """Si ce test échoue : une colonne `…token…`, `…key…`, `…hash…`, `…secret…` vient d'être
    ajoutée. Marque-la `info={"export": False}` si c'est un secret ; sinon écris pourquoi elle n'en
    est pas un en l'ajoutant à `REVIEWED_NOT_SECRET`."""
    assert unreviewed_secret_columns(Base.metadata) == []


def test_a_new_refresh_token_column_without_a_mark_fails_the_guard() -> None:
    metadata = MetaData()
    _table(metadata, "users", Column("refresh_token", Text))
    assert unreviewed_secret_columns(metadata) == ["users.refresh_token"]


def test_a_new_token_table_without_a_mark_fails_the_guard() -> None:
    metadata = MetaData()
    _table(metadata, "mcp_tokens", Column("token_hash", String(64)))
    assert unreviewed_secret_columns(metadata) == ["mcp_tokens.token_hash"]


def test_a_marked_column_or_table_passes_the_guard() -> None:
    metadata = MetaData()
    _table(metadata, "users", Column("refresh_token", Text, info={"export": False}))
    _table(metadata, "mcp_tokens", Column("token_hash", String(64)), export=False)
    assert unreviewed_secret_columns(metadata) == []


def test_a_reviewed_column_passes_the_guard() -> None:
    metadata = MetaData()
    _table(metadata, "documents", Column("storage_key", String(100)))
    assert "documents.storage_key" in REVIEWED_NOT_SECRET
    assert unreviewed_secret_columns(metadata) == []


def test_only_scoped_tables_are_guarded() -> None:
    metadata = MetaData()
    Table("unscoped", metadata, Column("id", String(36), primary_key=True), Column("token", Text))
    assert unreviewed_secret_columns(metadata) == []


def test_the_secrets_of_the_application_are_marked_in_the_models() -> None:
    api_keys = Base.metadata.tables["api_keys"]
    assert api_keys.c.encrypted_key.info == {"export": False}
    assert Base.metadata.tables["auth_sessions"].info == {"export": False}
    assert "auth_sessions" not in {table.name for table in user_tables()}
    assert "encrypted_key" not in [c.name for c in exported_columns(api_keys)]


def test_a_marked_column_is_left_out_of_the_export_columns() -> None:
    metadata = MetaData()
    table = _table(metadata, "users", Column("refresh_token", Text, info={"export": False}))
    assert [c.name for c in exported_columns(table)] == ["id", "user_id"]
