"""Translate resource codes in the library, pending drafts and undo history."""

import sqlalchemy as sa

from alembic import op

revision = "0082"
down_revision = "0081"

_RESOURCES = sa.table("resources", sa.column("type"), sa.column("level"))
_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))
_CODES = (
    ("type", "cours", "course"),
    ("type", "depot", "repository"),
    ("type", "papier", "paper"),
    ("level", "debutant", "beginner"),
    ("level", "intermediaire", "intermediate"),
    ("level", "avance", "advanced"),
)


def _rename_resource_snapshots(path: str, old: str, new: str) -> None:
    for snapshot in (_CHANGES.c.before, _CHANGES.c.after):
        matches = sa.case(
            (sa.func.json_valid(snapshot) == 1, sa.func.json_extract(snapshot, path) == old),
            else_=False,
        )
        op.execute(
            _CHANGES.update()
            .where(_CHANGES.c.table_name == "resources", matches)
            .values({snapshot: sa.func.json_set(snapshot, path, new)})
        )


def _rename_draft_array(
    table: str, column: str, array_path: str, field_path: str, old: str, new: str
) -> None:
    # Table and column identifiers come from the fixed migration call sites below.
    target = f'{table}."{column}"'
    scope = "AND table_name = 'lessons'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET "{column}" = json_set({target}, :array_path, json((
                SELECT json_group_array(json(resource))
                FROM (
                    SELECT CASE json_extract({target}, entry.fullkey || :field_path)
                        WHEN :old THEN json_set(entry.value, '$' || :field_path, :new)
                        ELSE {target} -> entry.fullkey
                    END AS resource
                    FROM json_each({target}, :array_path) AS entry
                    ORDER BY entry.key
                )
            )))
            WHERE CASE WHEN json_valid({target}) THEN
                json_type({target}, :array_path) = 'array' AND EXISTS (
                    SELECT 1 FROM json_each({target}, :array_path) AS entry
                    WHERE json_extract({target}, entry.fullkey || :field_path) = :old
                )
                ELSE 0
            END
            {scope}
            """  # noqa: S608
        ).bindparams(array_path=array_path, field_path=field_path, old=old, new=new)
    )


def _translate(reverse: bool) -> None:
    for field, old, new in _CODES:
        if reverse:
            old, new = new, old
        column = _RESOURCES.c[field]
        op.execute(_RESOURCES.update().where(column == old).values({column: new}))
        _rename_resource_snapshots(f"$.{field}", old, new)
        _rename_draft_array("lessons", "verification_draft", "$.resources", f".{field}", old, new)
        for snapshot in ("before", "after"):
            _rename_draft_array(
                "mcp_changes", snapshot, "$.verification_draft.resources", f".{field}", old, new
            )


def upgrade() -> None:
    _translate(reverse=False)


def downgrade() -> None:
    _translate(reverse=True)
