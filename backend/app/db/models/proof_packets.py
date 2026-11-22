from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class ProofPacket(UserScopedMixin, Base):
    __tablename__ = "proof_packets"

    title: Mapped[str] = mapped_column(String(120))
    digest: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[str] = mapped_column(Text)
