"""Use English codes for seniority in stored market scans."""

import sqlalchemy as sa

from alembic import op

revision = "0079"
down_revision = "0078"


def _rename(first: str, second: str, new_first: str, new_second: str) -> None:
    op.execute(
        sa.text(
            """
            UPDATE radar_runs
            SET postings = (
                SELECT json_group_array(json(posting))
                FROM (
                    SELECT CASE json_extract(postings, entry.fullkey || '.level')
                        WHEN :first THEN json_set(entry.value, '$.level', :new_first)
                        WHEN :second THEN json_set(entry.value, '$.level', :new_second)
                        ELSE postings -> entry.fullkey
                    END AS posting
                    FROM json_each(radar_runs.postings) AS entry
                    ORDER BY entry.key
                )
            )
            WHERE CASE WHEN json_valid(postings) THEN
                json_type(postings) = 'array' AND EXISTS (
                    SELECT 1 FROM json_each(radar_runs.postings) AS entry
                    WHERE json_extract(postings, entry.fullkey || '.level') IN (:first, :second)
                )
                ELSE 0
            END
            """
        ).bindparams(first=first, second=second, new_first=new_first, new_second=new_second)
    )


def upgrade() -> None:
    _rename("confirme", "inconnu", "mid_level", "unknown")


def downgrade() -> None:
    _rename("mid_level", "unknown", "confirme", "inconnu")
