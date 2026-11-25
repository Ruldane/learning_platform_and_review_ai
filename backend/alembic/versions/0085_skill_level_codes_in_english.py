"""Update mastery levels in skills, memory, study outcomes and undo history."""

import sqlalchemy as sa

from alembic import op

revision = "0085"
down_revision = "0084"

_LEVELS = (
    ("declare", "declared"),
    ("en_cours", "in_progress"),
    ("valide", "validated"),
    ("prouve", "proven"),
)
_SKILLS = sa.table("user_skills", sa.column("level"))
_MEMORY = sa.table("memory_items", sa.column("kind"), sa.column("meta"))
_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))


def _level_matches(document: sa.ColumnClause, path: str, old: str) -> sa.Case:
    return sa.case(
        (sa.func.json_valid(document) == 1, sa.func.json_extract(document, path) == old),
        else_=False,
    )


def _rename_snapshots(old: str, new: str) -> None:
    for column in (_CHANGES.c.before, _CHANGES.c.after):
        for name, path in (("user_skills", "$.level"), ("memory_items", "$.meta.level")):
            update = _CHANGES.update().where(
                _CHANGES.c.table_name == name, _level_matches(column, path, old)
            )
            if name == "memory_items":
                acquire = sa.case(
                    (
                        sa.func.json_valid(column) == 1,
                        sa.func.json_extract(column, "$.kind") == "acquis",
                    ),
                    else_=False,
                )
                update = update.where(acquire)
            op.execute(update.values({column: sa.func.json_set(column, path, new)}))


def _rename_history(
    table: str, column: str, path: str, old: str, new: str, *, scope: str | None = None
) -> None:
    # The identifiers and SQL expressions here are fixed by the migration's call sites.
    document = f'{table}."{column}"'
    if path.endswith(".skills"):
        kind = "array"
        item_level = "CASE WHEN item.type = 'array' THEN json_extract(item.value, '$[1]') END"
        replacement = "json_set(item.value, '$[1]', :new)"
        aggregate = "json_group_array(json(changed))"
    else:
        kind = "object"
        item_level = "CASE WHEN item.type = 'text' THEN item.value END"
        replacement = "json_quote(:new)"
        aggregate = "json_group_object(item_key, json(changed))"
    where = "AND table_name = :scope" if scope else ""
    update = sa.text(
        f"""
        UPDATE {table}
        SET "{column}" = json_set({document}, :path, json((
            SELECT {aggregate} FROM (
                SELECT item.key AS item_key, CASE {item_level}
                    WHEN :old THEN {replacement}
                    ELSE {document} -> item.fullkey END AS changed
                FROM json_each({document}, :path) AS item
                ORDER BY item.key
            )
        )))
        WHERE CASE WHEN json_valid({document}) THEN
            json_type({document}, :path) = :kind AND EXISTS (
                SELECT 1 FROM json_each({document}, :path) AS item WHERE {item_level} = :old
            ) ELSE 0 END
        {where}
        """  # noqa: S608
    ).bindparams(path=path, kind=kind, old=old, new=new)
    op.execute(update.bindparams(scope=scope) if scope else update)


def _rename(old: str, new: str) -> None:
    op.execute(_SKILLS.update().where(_SKILLS.c.level == old).values(level=new))
    op.execute(
        _MEMORY.update()
        .where(_MEMORY.c.kind == "acquis", _level_matches(_MEMORY.c.meta, "$.level", old))
        .values(meta=sa.func.json_set(_MEMORY.c.meta, "$.level", new))
    )
    _rename_snapshots(old, new)
    _rename_history("skill_snapshots", "levels", "$", old, new)
    _rename_history("study_sessions", "outcome", "$.result.skills", old, new)
    for column in ("before", "after"):
        _rename_history("mcp_changes", column, "$.levels", old, new, scope="skill_snapshots")
        _rename_history(
            "mcp_changes", column, "$.outcome.result.skills", old, new, scope="study_sessions"
        )


def upgrade() -> None:
    for old, new in _LEVELS:
        _rename(old, new)


def downgrade() -> None:
    for old, new in _LEVELS:
        _rename(new, old)
