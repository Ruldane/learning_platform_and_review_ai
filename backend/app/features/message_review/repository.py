from datetime import date
from typing import Any

from sqlalchemy import and_, case, select, update
from sqlalchemy.dialects.sqlite import insert

from app.db.base import new_id, utcnow
from app.db.models.message_review import TelegramReviewChallenge, TelegramReviewSettings
from app.db.repository import UserScopedRepository


class ConsentRepository(UserScopedRepository[TelegramReviewSettings]):
    model = TelegramReviewSettings

    async def mine(self) -> TelegramReviewSettings | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def save(self, values: dict[str, Any]) -> TelegramReviewSettings:
        table = self.model
        statement = insert(table).values(user_id=self.user_id, consent_id=new_id(), **values)
        offered = statement.excluded
        same_connection = and_(
            table.enabled.is_(True),
            offered.enabled.is_(True),
            table.token_id == offered.token_id,
            table.chat_id == offered.chat_id,
        )
        stmt = statement.on_conflict_do_update(
            index_elements=[table.user_id],
            set_={
                **values,
                "updated_at": utcnow(),
                "consent_id": case((same_connection, table.consent_id), else_=offered.consent_id),
            },
        ).returning(table)
        return (await self.session.execute(stmt)).scalar_one()

    async def authorized(
        self, token_id: str, chat_id: str, *, lock: bool
    ) -> TelegramReviewSettings | None:
        table = self.model
        conditions = (
            table.user_id == self.user_id,
            table.enabled.is_(True),
            table.token_id == token_id,
            table.chat_id == chat_id,
        )
        if lock:
            # SQLite keeps the write lock during the reservation or the card's rating.
            stmt = (
                update(table)
                .where(*conditions)
                .values(updated_at=table.updated_at)
                .returning(table)
            )
            return (await self.session.execute(stmt)).scalar_one_or_none()
        return (await self.session.execute(select(table).where(*conditions))).scalar_one_or_none()


class ChallengeRepository(UserScopedRepository[TelegramReviewChallenge]):
    model = TelegramReviewChallenge

    async def for_day(self, day: date) -> TelegramReviewChallenge | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id, self.model.day == day)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def reserve(
        self, consent: TelegramReviewSettings, day: date, card_id: str
    ) -> TelegramReviewChallenge:
        return await self.add(consent_id=consent.consent_id, day=day, card_id=card_id)
