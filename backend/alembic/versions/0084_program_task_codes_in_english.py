"""Update task type codes in the schedule, saved versions and undo history."""

import sqlalchemy as sa

from alembic import op

revision = "0084"
down_revision = "0083"

_TASKS = sa.table("tasks", sa.column("type"))
_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))
_CODES = (("lire", "read"), ("regarder", "watch"), ("pratiquer", "practice"), ("projet", "project"))


def _rename_task_snapshots(old: str, new: str) -> None:
    for snapshot in (_CHANGES.c.before, _CHANGES.c.after):
        matches = sa.case(
            (sa.func.json_valid(snapshot) == 1, sa.func.json_extract(snapshot, "$.type") == old),
            else_=False,
        )
        op.execute(
            _CHANGES.update()
            .where(_CHANGES.c.table_name == "tasks", matches)
            .values({snapshot: sa.func.json_set(snapshot, "$.type", new)})
        )


def _rename_version_tasks(table: str, column: str, weeks_path: str, old: str, new: str) -> None:
    # The table and column identifiers are fixed by the call sites below.
    document = f'{table}."{column}"'
    scope = "AND table_name = 'plan_versions'" if table == "mcp_changes" else ""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET "{column}" = (
                WITH RECURSIVE paths AS MATERIALIZED (
                    SELECT row_number() OVER (ORDER BY week.key, module.key, task.key) AS n,
                        week.fullkey || substr(module.fullkey, 2) ||
                        substr(task.fullkey, 2) || '.type' AS path
                    FROM json_each({document}, :weeks_path) AS week
                    JOIN json_each(
                        CASE WHEN week.type = 'object' THEN week.value ELSE '{{}}' END, '$.modules'
                    ) AS module
                    JOIN json_each(
                        CASE WHEN module.type = 'object' THEN module.value ELSE '{{}}' END,
                        '$.tasks'
                    ) AS task
                    WHERE typeof(week.key) = 'integer' AND typeof(module.key) = 'integer'
                        AND typeof(task.key) = 'integer'
                        AND CASE WHEN task.type = 'object'
                            THEN json_extract(task.value, '$.type') = :old ELSE 0 END
                ), rewritten(n, data) AS (
                    SELECT 0, {document}
                    UNION ALL
                    SELECT paths.n, json_set(rewritten.data, paths.path, :new)
                    FROM rewritten JOIN paths ON paths.n = rewritten.n + 1
                )
                SELECT data FROM rewritten ORDER BY n DESC LIMIT 1
            )
            WHERE CASE WHEN json_valid({document})
                THEN json_type({document}, :weeks_path) = 'array' ELSE 0 END
                AND instr({document}, :old) > 0
            {scope}
            """  # noqa: S608
        ).bindparams(weeks_path=weeks_path, old=old, new=new)
    )


def _rename(old: str, new: str) -> None:
    op.execute(_TASKS.update().where(_TASKS.c.type == old).values(type=new))
    _rename_task_snapshots(old, new)
    _rename_version_tasks("plan_versions", "snapshot", "$.weeks", old, new)
    for column in ("before", "after"):
        _rename_version_tasks("mcp_changes", column, "$.snapshot.weeks", old, new)


def upgrade() -> None:
    for old, new in _CODES:
        _rename(old, new)


def downgrade() -> None:
    for old, new in _CODES:
        _rename(new, old)
