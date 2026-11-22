"""Un dossier de répétition, indépendant d’une candidature réelle."""

from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class RecruitmentProcess(Base, UserScopedMixin):
    __tablename__ = "recruitment_processes"

    posting_id: Mapped[str] = mapped_column(String(36))
    offer: Mapped[dict[str, Any]]
    project: Mapped[dict[str, Any] | None]
    rubric: Mapped[list[Any]]
    missing_proofs: Mapped[list[Any]]
    steps: Mapped[list[Any]]
