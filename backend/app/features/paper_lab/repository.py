"""Accès par compte aux expériences issues d’un article."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.paper_lab import PaperLab


class PaperLabRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self.db, self.user_id = db, user_id

    async def list(self) -> list[PaperLab]:
        query = (
            select(PaperLab)
            .where(PaperLab.user_id == self.user_id)
            .order_by(PaperLab.created_at.desc())
            .limit(25)
        )
        return list((await self.db.scalars(query)).all())

    async def require(self, lab_id: str) -> PaperLab:
        query = select(PaperLab).where(PaperLab.id == lab_id, PaperLab.user_id == self.user_id)
        row = await self.db.scalar(query)
        if row is None:
            raise AppError("paper_lab_not_found", "Expérience introuvable.", 404)
        return row

    async def claim_publication(self, row: PaperLab) -> bool:
        query = (
            update(PaperLab)
            .where(
                PaperLab.id == row.id,
                PaperLab.user_id == self.user_id,
                PaperLab.session_id == row.session_id,
                PaperLab.stage == "queued",
            )
            .values(stage="ready")
            .returning(PaperLab.id)
        )
        return (await self.db.execute(query)).scalar_one_or_none() is not None
