from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class PortfolioDraft(UserScopedMixin, Base):
    __tablename__ = "portfolio_drafts"

    digest: Mapped[str] = mapped_column(String(64))
    html_key: Mapped[str]
    zip_key: Mapped[str]


class PortfolioSite(UserScopedMixin, Base):
    __tablename__ = "portfolio_sites"
    __table_args__ = (UniqueConstraint("user_id"),)

    slug: Mapped[str] = mapped_column(String(200))
    draft_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("portfolio_drafts.id", ondelete="SET NULL")
    )
    published_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("portfolio_drafts.id", ondelete="SET NULL")
    )
    published_url: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    use_in_cv: Mapped[bool] = mapped_column(default=False)
    use_in_kit: Mapped[bool] = mapped_column(default=False)
