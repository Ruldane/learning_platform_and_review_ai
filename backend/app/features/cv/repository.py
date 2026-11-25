"""Master profile versions (D118, D124), CV templates (D126), reviews, modifications and CV
versions (D130). Every query filters by `user_id`."""

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
        """The version with the highest number (of this status)."""
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
        """The highest version number, 0 without a profile."""
        stmt = select(func.max(MasterProfile.version)).where(MasterProfile.user_id == self.user_id)
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    async def all_versions(self) -> builtins.list[MasterProfile]:
        """All versions, most recent first."""
        stmt = (
            select(MasterProfile)
            .where(MasterProfile.user_id == self.user_id)
            .order_by(MasterProfile.version.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class TemplateRepository(UserScopedRepository[CvTemplate]):
    """CV templates (D126); archived ones are only returned by `get`."""

    model = CvTemplate

    async def visible(self) -> builtins.list[CvTemplate]:
        """The non-archived templates, most recent first."""
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
        """Templates already prepared (reusable font sets stored), archived included."""
        stmt = select(CvTemplate).where(
            CvTemplate.user_id == self.user_id, CvTemplate.prepared.is_not(None)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def in_review(self, template_id: str) -> bool:
        """A review in progress (started or proposed) uses this template."""
        stmt = select(CvReview.id).where(
            CvReview.user_id == self.user_id,
            CvReview.template_id == template_id,
            CvReview.status.in_(("running", "proposed")),
        )
        return (await self.session.execute(stmt.limit(1))).first() is not None


class ReviewRepository(UserScopedRepository[CvReview]):
    """CV reviews (D130)."""

    model = CvReview

    async def recent(self, posting_id: str | None = None) -> builtins.list[CvReview]:
        """The reviews (of an offer), most recent first."""
        stmt = select(CvReview).where(CvReview.user_id == self.user_id)
        if posting_id is not None:
            stmt = stmt.where(CvReview.posting_id == posting_id)
        stmt = stmt.order_by(CvReview.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_rows(self) -> builtins.list[CvReview]:
        """Reviews in progress (started or proposed)."""
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
        """In the order in which they were stored."""
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
        """The versions (of an offer, of reviews), most recent first."""
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
        """The next number for the offer (numbers are counted per offer)."""
        stmt = select(func.max(CvVersion.number)).where(
            CvVersion.user_id == self.user_id, CvVersion.posting_id == posting_id
        )
        return int((await self.session.execute(stmt)).scalar_one_or_none() or 0) + 1

    async def ready_latest(self) -> dict[str, tuple[str, int]]:
        """For each offer that has a ready version: `(identifier, number)` of the most recent one
        (the highest number). Read only, for applications."""
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
        """`identifier → number` of the given versions (the user's)."""
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
    """Company records (shared by offers and reviews), keyed by `company_key`."""

    model = Company

    async def by_key(self, name_norm: str) -> Company | None:
        stmt = select(Company).where(
            Company.user_id == self.user_id, Company.name_norm == name_norm
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


class AtsSourceRepository(UserScopedRepository[Source]):
    """The retained sources of the ATS refresh (P14): `web_research` session with subject
    `ats_refresh`, finished (`updated_at`: the end of a session)."""

    model = Source

    async def latest_session(self, since: datetime) -> str | None:
        """The last completed refresh session since `since` that kept at least one source: a
        recent refresh with no retained source does not hide the previous one."""
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
        """Its "kept" sources, best rated first."""
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
