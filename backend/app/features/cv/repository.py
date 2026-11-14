"""Versions du profil maître (D118, D124) et gabarits de CV (D126). Chaque requête filtre par
`user_id`."""

import builtins

from sqlalchemy import func, select

from app.db.models.career import CvReview, CvTemplate, MasterProfile, ProfileStatus
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


class TemplateRepository(UserScopedRepository[CvTemplate]):
    """Gabarits de CV (D126) ; les archivés ne sont rendus que par `get`."""

    model = CvTemplate

    async def visible(self) -> builtins.list[CvTemplate]:
        """Les gabarits non archivés, le plus récent d'abord."""
        stmt = (
            select(CvTemplate)
            .where(CvTemplate.user_id == self.user_id, CvTemplate.status != "archived")
            .order_by(CvTemplate.created_at.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def capturing(self) -> builtins.list[CvTemplate]:
        stmt = select(CvTemplate).where(
            CvTemplate.user_id == self.user_id, CvTemplate.status == "capturing"
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def active(self) -> CvTemplate | None:
        stmt = select(CvTemplate).where(CvTemplate.user_id == self.user_id, CvTemplate.active)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def prepared_rows(self) -> builtins.list[CvTemplate]:
        """Gabarits déjà préparés (polices rangées réutilisables), archivés compris."""
        stmt = select(CvTemplate).where(
            CvTemplate.user_id == self.user_id, CvTemplate.prepared.is_not(None)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def in_review(self, template_id: str) -> bool:
        """Une revue en cours (lancée ou proposée) emploie ce gabarit."""
        stmt = select(CvReview.id).where(
            CvReview.user_id == self.user_id,
            CvReview.template_id == template_id,
            CvReview.status.in_(("running", "proposed")),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None
