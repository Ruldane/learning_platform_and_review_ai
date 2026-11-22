from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class MentorShare(UserScopedMixin, Base):
    __tablename__ = "mentor_shares"

    packet_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(120))
    digest: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(String(64), info={"export": False})
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class MentorComment(UserScopedMixin, Base):
    __tablename__ = "mentor_comments"

    share_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mentor_shares.id", ondelete="CASCADE"), index=True
    )
    proof_id: Mapped[str] = mapped_column(String(36))
    text: Mapped[str] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(default=False, server_default=false())
