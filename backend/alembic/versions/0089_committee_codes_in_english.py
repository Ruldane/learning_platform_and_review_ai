"""Translate company size codes, committee votes, and verdicts."""

import sqlalchemy as sa

from alembic import op

revision = "0089"
down_revision = "0088"

_SIZES = (("pme", "sme"), ("grand_groupe", "large_company"), ("inconnu", "unknown"))
_VOTES = (("oui", "yes"), ("non", "no"), ("peut_etre", "maybe"))


def _replace_value(
    table: str,
    column: str,
    path: str,
    old: str,
    new: str,
    *,
    recorded_table: str | None = None,
) -> None:
    # Identifiers come from the fixed call sites below.
    document = f'"{column}"'
    scope = "AND table_name = :recorded_table" if recorded_table else ""
    statement = sa.text(
        f"""
        UPDATE {table}
        SET {document} = json_set({document}, :path, :new)
        WHERE CASE WHEN json_valid({document}) THEN
            json_extract({document}, :path) = :old ELSE 0 END
        {scope}
        """  # noqa: S608
    ).bindparams(path=path, old=old, new=new)
    if recorded_table:
        statement = statement.bindparams(recorded_table=recorded_table)
    op.execute(statement)


def _replace_votes(table: str, column: str, path: str, old: str, new: str) -> None:
    document = f'{table}."{column}"'
    scope = "AND table_name = 'committee_runs'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET "{column}" = json_set({document}, :path, json((
                SELECT json_group_array(json(changed))
                FROM (
                    SELECT CASE json_extract({document}, entry.fullkey || '.vote')
                        WHEN :old THEN json_set(entry.value, '$.vote', :new)
                        ELSE {document} -> entry.fullkey
                    END AS changed
                    FROM json_each({document}, :path) AS entry
                    ORDER BY entry.key
                )
            )))
            WHERE CASE WHEN json_valid({document}) THEN
                json_type({document}, :path) = 'array' AND EXISTS (
                    SELECT 1 FROM json_each({document}, :path) AS entry
                    WHERE json_extract({document}, entry.fullkey || '.vote') = :old
                )
                ELSE 0
            END
            {scope}
            """  # noqa: S608
        ).bindparams(path=path, old=old, new=new)
    )


def _translate(*, reverse: bool) -> None:
    for old, new in _SIZES:
        if reverse:
            old, new = new, old
        _replace_value("companies", "dossier", "$.size", old, new)
        for snapshot in ("before", "after"):
            _replace_value(
                "mcp_changes", snapshot, "$.dossier.size", old, new, recorded_table="companies"
            )
    for old, new in _VOTES:
        if reverse:
            old, new = new, old
        op.execute(
            sa.text("UPDATE committee_runs SET verdict = :new WHERE verdict = :old").bindparams(
                old=old, new=new
            )
        )
        _replace_votes("committee_runs", "votes", "$", old, new)
        for snapshot in ("before", "after"):
            _replace_value(
                "mcp_changes", snapshot, "$.verdict", old, new, recorded_table="committee_runs"
            )
            _replace_votes("mcp_changes", snapshot, "$.votes", old, new)


def upgrade() -> None:
    _translate(reverse=False)


def downgrade() -> None:
    _translate(reverse=True)
