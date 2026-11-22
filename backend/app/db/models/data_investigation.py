from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class DataInvestigation(UserScopedMixin, Base):
    __tablename__ = "data_investigations"

    dataset: Mapped[dict[str, Any]]
    source_rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    source_digest: Mapped[str] = mapped_column(String(64))
    operations: Mapped[list[Any]] = mapped_column(JSON, default=list)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
