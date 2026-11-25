"""Use English codes for week stages and their undo snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "0083"
down_revision = "0082"

_WEEKS = sa.table("weeks", sa.column("stage"))
_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))
_STAGES = (("fondations", "foundations"), ("pratique", "practice"), ("avance", "advanced"))


def _rename(old: str, new: str) -> None:
    op.execute(_WEEKS.update().where(_WEEKS.c.stage == old).values(stage=new))
    for snapshot in (_CHANGES.c.before, _CHANGES.c.after):
        matches = sa.case(
            (sa.func.json_valid(snapshot) == 1, sa.func.json_extract(snapshot, "$.stage") == old),
            else_=False,
        )
        op.execute(
            _CHANGES.update()
            .where(_CHANGES.c.table_name == "weeks", matches)
            .values({snapshot: sa.func.json_set(snapshot, "$.stage", new)})
        )


def upgrade() -> None:
    for old, new in _STAGES:
        _rename(old, new)


def downgrade() -> None:
    for old, new in _STAGES:
        _rename(new, old)
