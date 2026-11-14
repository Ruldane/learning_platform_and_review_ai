"""Versions du profil maître (D118, D124), gabarits de CV (D126), revues, modifications et
versions de CV (D130). Chaque requête filtre par `user_id`."""

import builtins
from collections.abc import Collection

from sqlalchemy import func, literal_column, select

from app.db.models.career import (
    CvModification,
    CvReview,
    CvTemplate,
    CvVersion,
    MasterProfile,
    ProfileStatus,
)
from app.db.models.postings import Company
from app.db.repository import UserScopedRepository

OPEN_REVIEW = ("running", "proposed")


class ProfileRepository(UserScopedRepository[MasterProfile]):
    model = MasterProfile

    async def latest(self, status: ProfileStatus | None = None) -> MasterProfile | None:
        """La version au plus grand numéro (de ce statut)."""
        stmt = select(MasterProfile).where(MasterProfile.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(MasterProfile.status == status)
        stmt = stmt.order_by(MasterProfile.version.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_version(self, version: int) -> MasterProfile | None:
        stmt = select(MasterProfile).where(
            MasterProfile.user_id == self.user_id, MasterProfile.version == version
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

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


class ReviewRepository(UserScopedRepository[CvReview]):
    """Revues de CV (D130)."""

    model = CvReview

    async def recent(self, posting_id: str | None = None) -> builtins.list[CvReview]:
        """Les revues (d'une offre), la plus récente d'abord."""
        stmt = select(CvReview).where(CvReview.user_id == self.user_id)
        if posting_id is not None:
            stmt = stmt.where(CvReview.posting_id == posting_id)
        stmt = stmt.order_by(CvReview.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_rows(self) -> builtins.list[CvReview]:
        """Revues en cours (lancées ou proposées)."""
        stmt = select(CvReview).where(
            CvReview.user_id == self.user_id, CvReview.status.in_(OPEN_REVIEW)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_on(self, posting_id: str) -> CvReview | None:
        stmt = select(CvReview).where(
            CvReview.user_id == self.user_id,
            CvReview.posting_id == posting_id,
            CvReview.status.in_(OPEN_REVIEW),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def by_session(self, session_id: str) -> CvReview | None:
        stmt = select(CvReview).where(
            CvReview.user_id == self.user_id, CvReview.session_id == session_id
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


class ModificationRepository(UserScopedRepository[CvModification]):
    model = CvModification

    async def of_review(self, review_id: str) -> builtins.list[CvModification]:
        """Dans l'ordre où elles ont été rangées."""
        stmt = (
            select(CvModification)
            .where(CvModification.user_id == self.user_id, CvModification.review_id == review_id)
            .order_by(CvModification.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def of_reviews(
        self, review_ids: Collection[str]
    ) -> builtins.dict[str, builtins.list[CvModification]]:
        out: builtins.dict[str, builtins.list[CvModification]] = {i: [] for i in review_ids}
        if not review_ids:
            return out
        stmt = (
            select(CvModification)
            .where(
                CvModification.user_id == self.user_id,
                CvModification.review_id.in_(builtins.list(review_ids)),
            )
            .order_by(CvModification.created_at, literal_column("rowid"))
        )
        for row in (await self.session.execute(stmt)).scalars():
            out[row.review_id].append(row)
        return out


class VersionRepository(UserScopedRepository[CvVersion]):
    model = CvVersion

    async def recent(
        self, *, posting_id: str | None = None, review_ids: Collection[str] | None = None
    ) -> builtins.list[CvVersion]:
        """Les versions (d'une offre, de revues), la plus récente d'abord."""
        stmt = select(CvVersion).where(CvVersion.user_id == self.user_id)
        if posting_id is not None:
            stmt = stmt.where(CvVersion.posting_id == posting_id)
        if review_ids is not None:
            stmt = stmt.where(CvVersion.review_id.in_(builtins.list(review_ids)))
        stmt = stmt.order_by(CvVersion.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def rendering(self, review_ids: Collection[str]) -> builtins.list[CvVersion]:
        if not review_ids:
            return []
        stmt = select(CvVersion).where(
            CvVersion.user_id == self.user_id,
            CvVersion.review_id.in_(builtins.list(review_ids)),
            CvVersion.status == "rendering",
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def next_number(self, posting_id: str) -> int:
        """Le numéro suivant pour l'offre (les numéros comptent par offre)."""
        stmt = select(func.max(CvVersion.number)).where(
            CvVersion.user_id == self.user_id, CvVersion.posting_id == posting_id
        )
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0) + 1

    async def get_fresh(self, version_id: str) -> CvVersion | None:
        stmt = (
            select(CvVersion)
            .where(CvVersion.id == version_id, CvVersion.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class CompanyRepository(UserScopedRepository[Company]):
    """Fiches d'entreprise (partagées par les offres et les revues), par clé `company_key`."""

    model = Company

    async def by_key(self, name_norm: str) -> Company | None:
        stmt = select(Company).where(
            Company.user_id == self.user_id, Company.name_norm == name_norm
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
