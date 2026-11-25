"""Use English codes for seniority in stored job posting analyses."""

import sqlalchemy as sa

from alembic import op

revision = "0077"
down_revision = "0076"


def _rename(first: str, second: str, new_first: str, new_second: str) -> None:
    op.execute(
        sa.text(
            """
            UPDATE job_postings
            SET analysis = json_set(
                analysis,
                '$.level',
                CASE json_extract(analysis, '$.level')
                    WHEN :first THEN :new_first
                    ELSE :new_second
                END
            )
            WHERE CASE WHEN json_valid(analysis)
                THEN json_extract(analysis, '$.level') IN (:first, :second)
                ELSE 0
            END
            """
        ).bindparams(first=first, second=second, new_first=new_first, new_second=new_second)
    )


def upgrade() -> None:
    _rename("confirme", "inconnu", "mid_level", "unknown")


def downgrade() -> None:
    _rename("mid_level", "unknown", "confirme", "inconnu")
