"""carrière (profil maître, gabarits, offres, entreprises, revues, modifications, versions de CV)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-13 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enfants avant parents (clés étrangères) ; les index suivent leur table.
CAREER_TABLES = (
    "cv_versions",
    "cv_modifications",
    "cv_reviews",
    "cv_templates",
    "master_profile",
    "companies",
    "job_postings",
)


def _s(name: str, length: int, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.String(length=length), nullable=null)


def _t(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Text(), nullable=null)


def _i(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Integer(), nullable=null)


def _b(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.Boolean(), nullable=False)


def _j(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.JSON(), nullable=null)


def _dt(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=null)


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"), ondelete="CASCADE"
    )


def _uq(table: str, *columns: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*columns, name=op.f(f"uq_{table}_{columns[0]}"))


def _create(
    table: str,
    *items: Any,
    indexes: dict[str, list[str]] | None = None,
    partial: dict[str, tuple[list[str], str]] | None = None,
) -> None:
    """Crée la table avec les colonnes communes (`UserScopedMixin`), ses index et ses index
    uniques partiels (`nom → (colonnes, condition)`)."""
    op.create_table(
        table,
        *items,
        _s("id", 36),
        _s("user_id", 36),
        _dt("created_at"),
        _dt("updated_at"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    )
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.create_index(batch_op.f(f"ix_{table}_user_id"), ["user_id"], unique=False)
        for name, columns in (indexes or {}).items():
            batch_op.create_index(name, columns, unique=False)
        for name, (columns, where) in (partial or {}).items():
            batch_op.create_index(name, columns, unique=True, sqlite_where=sa.text(where))


def _create_posting_tables() -> None:
    _create(
        "job_postings",
        _t("url", True),
        _s("url_norm", 2048, True),
        _s("source", 8),
        _s("company", 200, True),
        _s("company_norm", 200, True),
        _s("title", 200, True),
        _t("text"),
        _s("text_hash", 64),
        _s("status", 12),
        _j("analysis", True),
        _j("duplicates"),
        _j("distinct_from"),
        _s("memory_item_id", 36, True),
        _j("gap", True),
        _s("gap_session_id", 36, True),
        _s("failure_reason", 300, True),
        indexes={"ix_job_postings_company_title": ["user_id", "company_norm", "title"]},
        partial={
            "uq_job_postings_url": (["user_id", "url_norm"], "url_norm IS NOT NULL"),
            "uq_job_postings_text": (["user_id", "text_hash"], "url_norm IS NULL"),
        },
    )
    _create(
        "companies",
        _s("name", 200),
        _s("name_norm", 200),
        _j("brief", True),
        _j("sources"),
        _s("ats", 40, True),
        _dt("refreshed_at", True),
        _uq("companies", "user_id", "name_norm"),
    )


def _create_profile_tables() -> None:
    _create(
        "master_profile",
        _i("version"),
        _s("status", 12),
        _j("data"),
        _s("source", 16),
        _s("session_id", 36, True),
        _j("document_ids"),
        _j("dropped"),
        _uq("master_profile", "user_id", "version"),
    )
    _create(
        "cv_templates",
        _s("document_id", 36),
        _s("name", 120),
        _s("status", 12),
        _b("active"),
        _j("spec", True),
        _t("html", True),
        _t("css", True),
        _j("fonts"),
        _j("font_gaps"),
        _i("score", True),
        _j("score_detail", True),
        _i("passes"),
        _i("page_count"),
        _j("page_size"),
        _j("original_pages"),
        _j("render_pages"),
        _j("sample_content", True),
        _b("selectable"),
        _s("session_id", 36, True),
        _s("failure_reason", 300, True),
        partial={"uq_cv_templates_active": (["user_id"], "active = 1")},
    )


def _create_review_tables() -> None:
    _create(
        "cv_reviews",
        _s("posting_id", 36),
        _s("template_id", 36),
        _i("profile_version"),
        _s("session_id", 36, True),
        _s("status", 12),
        _j("before", True),
        _j("after", True),
        _j("report", True),
        _j("keywords_to_gap"),
        _s("company_id", 36, True),
        _fk("cv_reviews", "posting_id", "job_postings"),
    )
    _create(
        "cv_modifications",
        _s("review_id", 36),
        _s("ref", 8),
        _s("section", 16),
        _s("action", 8),
        _s("target", 40, True),
        _t("before"),
        _t("after"),
        _t("reason"),
        _s("type", 12),
        _j("fact_ids"),
        _s("status", 12),
        _j("blocks"),
        _s("author", 32),
        _dt("decided_at", True),
        _fk("cv_modifications", "review_id", "cv_reviews"),
        _uq("cv_modifications", "review_id", "ref"),
    )


def _create_version_table() -> None:
    _create(
        "cv_versions",
        _s("review_id", 36),
        _s("posting_id", 36),
        _s("template_id", 36),
        _i("number"),
        _s("status", 16),
        _j("content"),
        _j("decisions"),
        _s("storage_key", 200, True),
        _s("filename", 160),
        _i("page_count", True),
        _i("original_page_count"),
        _b("allow_extra_pages"),
        _j("page_images"),
        _j("ats", True),
        _j("coverage", True),
        _s("failure_reason", 300, True),
        _fk("cv_versions", "review_id", "cv_reviews"),
        _uq("cv_versions", "posting_id", "number"),
        indexes={"ix_cv_versions_user_review": ["user_id", "review_id"]},
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_posting_tables()
    _create_profile_tables()
    _create_review_tables()
    _create_version_table()


def downgrade() -> None:
    """Downgrade schema."""
    for table in CAREER_TABLES:
        op.drop_table(table)
