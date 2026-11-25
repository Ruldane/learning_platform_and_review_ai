"""Rename the page regions in stored CV comparisons and undo history."""

import sqlalchemy as sa

from alembic import op

revision = "0090"
down_revision = "0089"

_REGIONS = (
    ("haut", "top"),
    ("milieu", "middle"),
    ("bas", "bottom"),
    ("gauche", "left"),
    ("droite", "right"),
)


def _rename(table: str, column: str, root: str, old: str, new: str) -> None:
    """Apply ordered updates to the region codes inside a comparison document."""
    document = f'source."{column}"'
    scope = "source.table_name = 'cv_templates' AND" if table == "mcp_changes" else ""
    statement = sa.text(
        f"""
        WITH RECURSIVE edits AS (
            SELECT source.id, item.fullkey AS path,
                CASE WHEN item.key = :old THEN item.path || '.' || :new END AS shift_path,
                row_number() OVER (PARTITION BY source.id ORDER BY item.id) AS position
            FROM {table} AS source, json_tree(
                CASE WHEN json_valid({document}) THEN {document} END
            ) AS item
            WHERE {scope} (
                (item.atom = :old AND (item.fullkey GLOB :zones OR item.fullkey GLOB :matches))
                OR (item.key = :old AND item.path GLOB :shifts)
            )
        ), rewritten(id, position, document) AS (
            SELECT id, 0, "{column}" FROM {table} WHERE id IN (SELECT id FROM edits)
            UNION ALL
            SELECT prior.id, edit.position,
                CASE WHEN edit.shift_path IS NULL THEN json_set(prior.document, edit.path, :new)
                ELSE json_remove(
                    json_insert(prior.document, edit.shift_path, prior.document -> edit.path),
                    edit.path
                ) END
            FROM rewritten AS prior
            JOIN edits AS edit ON edit.id = prior.id AND edit.position = prior.position + 1
        )
        UPDATE {table}
        SET "{column}" = (
            SELECT document FROM rewritten WHERE rewritten.id = {table}.id
            ORDER BY position DESC LIMIT 1
        )
        WHERE id IN (SELECT id FROM edits)
        """  # noqa: S608
    ).bindparams(
        old=old,
        new=new,
        zones=f"{root}.zones[[]*].zone",
        matches=f"{root}.matches[[]*].zone",
        shifts=f"{root}.shifts",
    )
    op.execute(statement)


def _translate(*, reverse: bool) -> None:
    for old, new in _REGIONS:
        if reverse:
            old, new = new, old
        _rename("cv_templates", "score_detail", "$", old, new)
        _rename("cv_templates", "pass_log", "$[[]*].similarity", old, new)
        for snapshot in ("before", "after"):
            # SQLite's json_tree quotes keys containing underscores in its paths.
            _rename("mcp_changes", snapshot, '$."score_detail"', old, new)
            _rename("mcp_changes", snapshot, '$."pass_log"[[]*].similarity', old, new)


def upgrade() -> None:
    _translate(reverse=False)


def downgrade() -> None:
    _translate(reverse=True)
