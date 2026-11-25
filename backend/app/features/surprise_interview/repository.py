from datetime import date
from typing import Any

from sqlalchemy import and_, case, select, update
from sqlalchemy.dialects.sqlite import insert

from app.db.base import new_id, utcnow
from app.db.models.surprise_interview import SurpriseInvitation, SurpriseSettings
from app.db.repository import UserScopedRepository
from app.features.surprise_interview.schemas import SurprisePreferences


class SettingsRepository(UserScopedRepository[SurpriseSettings]):
    model = SurpriseSettings

    async def mine(self) -> SurpriseSettings | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def save(self, body: SurprisePreferences, link_id: str | None) -> None:
        table = self.model
        values = {**body.model_dump(), "chat_consent_id": link_id}
        statement = insert(table).values(user_id=self.user_id, consent_id=new_id(), **values)
        offered = statement.excluded
        same = and_(
            table.enabled.is_(True),
            offered.enabled.is_(True),
            table.chat_consent_id == offered.chat_consent_id,
            table.token_id == offered.token_id,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[table.user_id],
                set_={
                    **values,
                    "consent_id": case((same, table.consent_id), else_=offered.consent_id),
                    "updated_at": utcnow(),
                },
            )
        )

    async def authorized(self, token_id: str, *, lock: bool) -> SurpriseSettings | None:
        table = self.model
        conditions = (
            table.user_id == self.user_id,
            table.enabled.is_(True),
            table.token_id == token_id,
        )
        if lock:
            stmt = (
                update(table)
                .where(*conditions)
                .values(updated_at=table.updated_at)
                .returning(table)
            )
            return (await self.session.execute(stmt)).scalar_one_or_none()
        return (await self.session.execute(select(table).where(*conditions))).scalar_one_or_none()


class InvitationRepository(UserScopedRepository[SurpriseInvitation]):
    model = SurpriseInvitation

    async def for_week(self, week: date) -> SurpriseInvitation | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id, self.model.week == week)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def save_receipts(self, invitation_id: str, answers: dict[str, Any]) -> None:
        # The MCP undo cannot restore the interruption. The transport receipt and its
        # acknowledgement are technical transitions, outside the undo history.
        table = self.model
        await self.session.execute(
            update(table)
            .where(table.user_id == self.user_id, table.id == invitation_id)
            .values(answers=answers, updated_at=utcnow())
        )
