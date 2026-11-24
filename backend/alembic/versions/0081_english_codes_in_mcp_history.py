"""Keep undo snapshots in step with the posting and quiz code migrations."""

import sqlalchemy as sa

from alembic import op

revision = "0081"
down_revision = "0080"

_CHANGES = sa.table("mcp_changes", sa.column("table_name"), sa.column("before"), sa.column("after"))
_CODES = (
    ("job_postings", "$.analysis.level", "confirme", "mid_level"),
    ("job_postings", "$.analysis.level", "inconnu", "unknown"),
    ("quiz_questions", "$.type", "qcm", "mcq"),
)


def _rename(table: str, path: str, old: str, new: str) -> None:
    for snapshot in (_CHANGES.c.before, _CHANGES.c.after):
        matches = sa.case(
            (sa.func.json_valid(snapshot) == 1, sa.func.json_extract(snapshot, path) == old),
            else_=False,
        )
        op.execute(
            _CHANGES.update()
            .where(_CHANGES.c.table_name == table, matches)
            .values({snapshot: sa.func.json_set(snapshot, path, new)})
        )


def upgrade() -> None:
    for table, path, old, new in _CODES:
        _rename(table, path, old, new)


def downgrade() -> None:
    for table, path, old, new in _CODES:
        _rename(table, path, new, old)
