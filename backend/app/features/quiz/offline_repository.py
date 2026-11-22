from datetime import date

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from app.db.models.offline_reviews import OfflineReview
from app.db.repository import UserScopedRepository


class OfflineReviewRepository(UserScopedRepository[OfflineReview]):
    model = OfflineReview

    async def reserve(self, receipt_id: str, card_id: str, due_date: date, ok: bool) -> str | None:
        stmt = (
            insert(OfflineReview)
            .values(
                user_id=self.user_id,
                receipt_id=receipt_id,
                card_id=card_id,
                due_date=due_date,
                ok=ok,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "receipt_id"])
            .returning(OfflineReview.id)
        )
        return await self.session.scalar(stmt)

    async def by_receipt(self, receipt_id: str) -> OfflineReview | None:
        stmt = select(OfflineReview).where(
            OfflineReview.user_id == self.user_id, OfflineReview.receipt_id == receipt_id
        )
        return await self.session.scalar(stmt)

    async def complete(self, reservation_id: str, response: dict[str, object]) -> None:
        await self.session.execute(
            update(OfflineReview)
            .where(OfflineReview.user_id == self.user_id, OfflineReview.id == reservation_id)
            .values(response=response)
        )
