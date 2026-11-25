"""Rename memory kinds in the database and in recorded changes and events."""

import sqlalchemy as sa

from alembic import op

revision = "0086"
down_revision = "0085"

_ITEMS = sa.table("memory_items", sa.column("kind"))
_WRITES = sa.table("memory_writes", sa.column("kind"))
_EVENTS = sa.table("session_events", sa.column("type"), sa.column("payload"))
_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))
_KINDS = (("acquis", "skill"), ("lecon", "lesson"), ("offre", "posting"))


def _kind_is(document: sa.ColumnClause, path: str, old: str) -> sa.Case:
    return sa.case(
        (sa.func.json_valid(document) == 1, sa.func.json_extract(document, path) == old),
        else_=False,
    )


def _rename(old: str, new: str) -> None:
    for table in (_ITEMS, _WRITES):
        op.execute(table.update().where(table.c.kind == old).values(kind=new))
    payload = _EVENTS.c.payload
    op.execute(
        _EVENTS.update()
        .where(_EVENTS.c.type == "memory.written", _kind_is(payload, "$.kind", old))
        .values(payload=sa.func.json_set(payload, "$.kind", new))
    )
    for snapshot in (_CHANGES.c.before, _CHANGES.c.after):
        op.execute(
            _CHANGES.update()
            .where(
                _CHANGES.c.table_name.in_(("memory_items", "memory_writes")),
                _kind_is(snapshot, "$.kind", old),
            )
            .values({snapshot: sa.func.json_set(snapshot, "$.kind", new)})
        )


def upgrade() -> None:
    for old, new in _KINDS:
        _rename(old, new)


def downgrade() -> None:
    for old, new in _KINDS:
        _rename(new, old)
