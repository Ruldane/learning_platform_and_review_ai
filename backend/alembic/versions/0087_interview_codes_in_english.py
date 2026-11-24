"""Rename interview criteria, question sources and score keys in saved results."""

import sqlalchemy as sa

from alembic import op

revision = "0087"
down_revision = "0086"

_EXCHANGE_CODES = (
    ("criterion", "clarte", "clarity"),
    ("criterion", "profondeur", "technical_depth"),
    ("criterion", "adequation", "role_fit"),
    ("source", "offre", "posting"),
    ("source", "dossier", "company_dossier"),
    ("source", "ecart", "gap"),
)
_SCORE_KEYS = (
    ("clarte", "clarity"),
    ("profondeur_technique", "technical_depth"),
    ("adequation", "role_fit"),
)


def _rename_exchange_field(
    table: str, column: str, path: str, field: str, old: str, new: str
) -> None:
    # The identifiers come from the fixed migration call sites below.
    document = f'{table}."{column}"'
    scope = "AND table_name = 'interviews'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET "{column}" = json_set({document}, :path, json((
                SELECT json_group_array(json(changed))
                FROM (
                    SELECT CASE json_extract({document}, entry.fullkey || :field)
                        WHEN :old THEN json_set(entry.value, '$' || :field, :new)
                        ELSE {document} -> entry.fullkey
                    END AS changed
                    FROM json_each({document}, :path) AS entry
                    ORDER BY entry.key
                )
            )))
            WHERE CASE WHEN json_valid({document}) THEN
                json_type({document}, :path) = 'array' AND EXISTS (
                    SELECT 1 FROM json_each({document}, :path) AS entry
                    WHERE json_extract({document}, entry.fullkey || :field) = :old
                )
                ELSE 0
            END
            {scope}
            """  # noqa: S608
        ).bindparams(path=path, field=f".{field}", old=old, new=new)
    )


def _rename_score_key(table: str, column: str, path: str, old: str, new: str) -> None:
    document = f'{table}."{column}"'
    scope = "AND table_name = 'interviews'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET "{column}" = json_remove(
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
    for field, old, new in _EXCHANGE_CODES:
        if reverse:
            old, new = new, old
        _rename_exchange_field("interviews", "exchanges", "$", field, old, new)
        for snapshot in ("before", "after"):
            _rename_exchange_field("mcp_changes", snapshot, "$.exchanges", field, old, new)
    for old, new in _SCORE_KEYS:
        if reverse:
            old, new = new, old
        _rename_score_key("interviews", "debrief", "$.scores", old, new)
        for snapshot in ("before", "after"):
            _rename_score_key("mcp_changes", snapshot, "$.debrief.scores", old, new)


def upgrade() -> None:
    _translate(reverse=False)


def downgrade() -> None:
    _translate(reverse=True)
