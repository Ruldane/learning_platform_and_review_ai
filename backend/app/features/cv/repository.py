"""Versions du profil maître (D118, D124), gabarits de CV (D126), revues, modifications et
versions de CV (D130). Chaque requête filtre par `user_id`."""

import builtins
from collections.abc import Collection
from datetime import datetime

from sqlalchemy import func, literal_column, select

from app.db.models.agents import AgentSession
from app.db.models.career import (
    OPEN_REVIEW_STATUSES,
    CvModification,
    CvReview,
    CvTemplate,
    CvVersion,
    MasterProfile,
    ProfileStatus,
)
from app.db.models.postings import Company
from app.db.models.research import Source
from app.db.repository import UserScopedRepository

OPEN_REVIEW = OPEN_REVIEW_STATUSES


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

    async def ready_latest(self) -> dict[str, tuple[str, int]]:
        """Pour chaque offre qui a une version prête : `(identifiant, numéro)` de la plus récente
        (le plus grand numéro). Lecture seule, pour les candidatures."""
        stmt = (
            select(CvVersion.posting_id, CvVersion.id, CvVersion.number)
            .where(CvVersion.user_id == self.user_id, CvVersion.status == "ready")
            .order_by(CvVersion.number)
        )
        return {
            posting_id: (version_id, number)
            for posting_id, version_id, number in (await self.session.execute(stmt)).all()
        }

    async def numbers(self, version_ids: Collection[str]) -> dict[str, int]:
        """`identifiant → numéro` des versions données (celles de l'utilisatrice)."""
        if not version_ids:
            return {}
        stmt = select(CvVersion.id, CvVersion.number).where(
            CvVersion.user_id == self.user_id, CvVersion.id.in_(builtins.list(version_ids))
        )
        return {
            version_id: number for version_id, number in (await self.session.execute(stmt)).all()
        }

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


class AtsSourceRepository(UserScopedRepository[Source]):
    """Les sources retenues du rafraîchissement ATS (P14) : session `web_research` de sujet
    `ats_refresh`, terminée (`updated_at` : la fin d'une session)."""

    model = Source

    async def latest_session(self, since: datetime) -> str | None:
        """La dernière session de rafraîchissement terminée depuis `since` qui a gardé au moins
        une source : un rafraîchissement récent sans aucune source retenue ne cache pas le
        précédent."""
        kept = (
            select(Source.id)
            .where(
                Source.user_id == self.user_id,
                Source.session_id == AgentSession.id,
                Source.verdict == "kept",
            )
            .exists()
        )
        stmt = (
            select(AgentSession.id)
            .where(
                AgentSession.user_id == self.user_id,
                AgentSession.graph == "web_research",
                AgentSession.subject_type == "ats_refresh",
                AgentSession.status == "completed",
                AgentSession.updated_at >= since,
                kept,
            )
            .order_by(AgentSession.updated_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def kept(self, session_id: str, limit: int) -> list[Source]:
        """Ses sources « kept », les mieux notées d'abord."""
        stmt = (
            select(Source)
            .where(
                Source.user_id == self.user_id,
                Source.session_id == session_id,
                Source.verdict == "kept",
            )
            .order_by(Source.score.desc(), Source.created_at, Source.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())
