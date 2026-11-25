from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class ProjectGithubClaim(UserScopedMixin, Base):
    """A pending GitHub profile challenge or a consumed commit attribution."""

    __tablename__ = "project_github_claims"
    __table_args__ = (
        Index("ix_project_github_claims_project", "user_id", "project_id"),
        Index(
            "uq_project_github_claims_confirmed_sha",
            "user_id",
            "sha",
            unique=True,
            sqlite_where=text("verified_at IS NOT NULL"),
        ),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    repository_id: Mapped[int] = mapped_column(BigInteger)
    owner: Mapped[str] = mapped_column(String(39))
    repository: Mapped[str] = mapped_column(String(100))
    sha: Mapped[str] = mapped_column(String(40))
    author_id: Mapped[int] = mapped_column(BigInteger)
    challenge_digest: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    session_id: Mapped[str | None] = mapped_column(String(36))
