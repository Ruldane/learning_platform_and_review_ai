from datetime import datetime

from sqlalchemy import ColumnElement, func, select, update

from app.db.models.mentor_reviews import MentorComment, MentorShare
from app.db.repository import UserScopedRepository


class MentorShares(UserScopedRepository[MentorShare]):
    model = MentorShare

    def _allowed(self, digest: str, now: datetime) -> tuple[ColumnElement[bool], ...]:
        return (
            self.model.user_id == self.user_id,
            self.model.token_hash == digest,
            self.model.expires_at > now,
            self.model.revoked_at.is_(None),
        )

    async def active(self, digest: str, now: datetime) -> MentorShare | None:
        statement = select(self.model).where(*self._allowed(digest, now))
        return await self.session.scalar(statement)

    async def claim_for_comment(self, digest: str, now: datetime) -> MentorShare | None:
        statement = (
            update(self.model)
            .where(*self._allowed(digest, now))
            .values(updated_at=now)
            .returning(self.model)
        )
        return await self.session.scalar(statement)

    async def revoke(self, share_id: str, now: datetime) -> bool:
        statement = (
            update(self.model)
            .where(self.model.id == share_id, self.model.user_id == self.user_id)
            .values(revoked_at=func.coalesce(self.model.revoked_at, now), updated_at=now)
            .returning(self.model.id)
        )
        return await self.session.scalar(statement) is not None

    async def history(self) -> list[MentorShare]:
        statement = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(statement))


class MentorComments(UserScopedRepository[MentorComment]):
    model = MentorComment

    async def for_share(self, share_id: str) -> list[MentorComment]:
        statement = (
            select(self.model)
            .where(self.model.share_id == share_id, self.model.user_id == self.user_id)
            .order_by(self.model.created_at, self.model.id)
        )
        return list(await self.session.scalars(statement))
