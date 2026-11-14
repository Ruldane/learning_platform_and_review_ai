"""Versions du profil maître (D118, D124) : la plus récente (d'un statut), celle d'une session,
toutes les versions. Chaque requête filtre par `user_id`."""

import builtins

from sqlalchemy import func, select

from app.db.models.career import MasterProfile, ProfileStatus
from app.db.repository import UserScopedRepository


class ProfileRepository(UserScopedRepository[MasterProfile]):
    model = MasterProfile

    async def latest(self, status: ProfileStatus | None = None) -> MasterProfile | None:
        """La version au plus grand numéro (de ce statut)."""
        stmt = select(MasterProfile).where(MasterProfile.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(MasterProfile.status == status)
        stmt = stmt.order_by(MasterProfile.version.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_session(self, session_id: str) -> MasterProfile | None:
        stmt = select(MasterProfile).where(
            MasterProfile.user_id == self.user_id, MasterProfile.session_id == session_id
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def top_version(self) -> int:
        """Le plus grand numéro de version, 0 sans profil."""
        stmt = select(func.max(MasterProfile.version)).where(MasterProfile.user_id == self.user_id)
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    async def all_versions(self) -> builtins.list[MasterProfile]:
        """Toutes les versions, la plus récente d'abord."""
        stmt = (
            select(MasterProfile)
            .where(MasterProfile.user_id == self.user_id)
            .order_by(MasterProfile.version.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
