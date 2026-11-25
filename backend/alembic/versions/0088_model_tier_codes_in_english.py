"""Rename model tiers in saved settings and pending MCP undo snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "0088"
down_revision = "0087"

_TIERS = (("rapide", "fast"), ("fort", "strong"))


def _rename_key(table: str, column: str, path: str, old: str, new: str) -> None:
    # Identifiers and paths come from the fixed call sites below.
    document = f'"{column}"'
    scope = "AND table_name = 'user_settings'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {document} = json_remove(
                CASE WHEN json_type({document}, :new_path) IS NULL
                    THEN json_set({document}, :new_path, {document} -> :old_path)
                    ELSE {document}
                END,
                :old_path
            )
            WHERE CASE WHEN json_valid({document}) THEN
                json_type({document}, :old_path) IS NOT NULL ELSE 0 END
            {scope}
            """  # noqa: S608
        ).bindparams(old_path=f"{path}.{old}", new_path=f"{path}.{new}")
    )


def _translate(*, reverse: bool) -> None:
    for old, new in _TIERS:
        if reverse:
            old, new = new, old
        _rename_key("user_settings", "data", "$.tiers", old, new)
        for snapshot in ("before", "after"):
            _rename_key("mcp_changes", snapshot, "$.data.tiers", old, new)


def upgrade() -> None:
    _translate(reverse=False)


def downgrade() -> None:
    _translate(reverse=True)
