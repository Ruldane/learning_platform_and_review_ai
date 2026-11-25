"""January's postings (D118, D122): reading by normalized link, by text fingerprint, by company or
by memory item; the analysis is set only once (`UPDATE … WHERE analysis IS NULL`). Each query
filters by `user_id`."""

import builtins
from collections.abc import Collection
from typing import Any

from sqlalchemy import func, literal_column, select, update

from app.db.models.applications import Application, CommitteeRun, Interview
from app.db.models.career import OPEN_REVIEW_STATUSES, CvReview, CvVersion
from app.db.models.postings import JobPosting
from app.db.repository import UserScopedRepository


class PostingRepository(UserScopedRepository[JobPosting]):
    model = JobPosting

    async def get_fresh(self, posting_id: str) -> JobPosting | None:
        """The posting re-read from the database (never the object held by the session)."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.id == posting_id, JobPosting.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_url_norm(self, url_norm: str) -> JobPosting | None:
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id, JobPosting.url_norm == url_norm
        )
        return (await self.session.execute(stmt.execution_options(populate_existing=True))).scalar()

    async def by_text_hash(self, text_hash: str) -> JobPosting | None:
        """The oldest posting with this text (pasted text first, then link)."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.user_id == self.user_id, JobPosting.text_hash == text_hash)
            .order_by(JobPosting.url_norm.is_not(None), JobPosting.created_at)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self) -> builtins.list[JobPosting]:
        """January's postings, most recent first."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.user_id == self.user_id)
            .order_by(JobPosting.created_at.desc(), literal_column("rowid").desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def same_company(self, company_norm: str, exclude_id: str) -> builtins.list[JobPosting]:
        """The other postings of this company (`company_key`), oldest first."""
        stmt = (
            select(JobPosting)
            .where(
                JobPosting.user_id == self.user_id,
                JobPosting.company_norm == company_norm,
                JobPosting.id != exclude_id,
            )
            .order_by(JobPosting.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def by_ids(self, ids: Collection[str]) -> dict[str, JobPosting]:
        if not ids:
            return {}
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id, JobPosting.id.in_(builtins.list(ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}

    async def by_memory_items(self, item_ids: Collection[str]) -> builtins.list[JobPosting]:
        if not item_ids:
            return []
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id,
            JobPosting.memory_item_id.in_(builtins.list(item_ids)),
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def claim_analysis(self, posting_id: str, **fields: Any) -> bool:
        """Sets the analysis and its fields if the posting has none yet; true if it is this one (the
        first one written wins, D121)."""
        stmt = (
            update(JobPosting)
            .where(
                JobPosting.id == posting_id,
                JobPosting.user_id == self.user_id,
                JobPosting.analysis.is_(None),
            )
            .values(**fields)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def item_shared(self, item_id: str, exclude_id: str) -> bool:
        """Does another posting point to the same memory item (same text)?"""
        stmt = select(func.count()).where(
            JobPosting.user_id == self.user_id,
            JobPosting.memory_item_id == item_id,
            JobPosting.id != exclude_id,
        )
        return bool((await self.session.execute(stmt)).scalar_one())

    async def running_reviews(self, posting_id: str) -> int:
        """The posting's CV reviews still open (started or proposed)."""
        stmt = select(func.count()).where(
            CvReview.user_id == self.user_id,
            CvReview.posting_id == posting_id,
            CvReview.status.in_(OPEN_REVIEW_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def version_files(self, posting_id: str) -> builtins.list[str]:
        """The stored keys of the posting's CV versions: PDF and page images."""
        stmt = select(CvVersion.storage_key, CvVersion.page_images).where(
            CvVersion.user_id == self.user_id, CvVersion.posting_id == posting_id
        )
        keys: builtins.list[str] = []
        for storage_key, images in (await self.session.execute(stmt)).all():
            keys += [key for key in (storage_key, *images) if isinstance(key, str) and key]
        return keys

    async def reviewed(self, posting_ids: Collection[str]) -> set[str]:
        """The postings that have at least one CV review."""
        if not posting_ids:
            return set()
        stmt = select(CvReview.posting_id).where(
            CvReview.user_id == self.user_id, CvReview.posting_id.in_(builtins.list(posting_ids))
        )
        return {row[0] for row in (await self.session.execute(stmt)).all()}

    async def running_work(self, posting_id: str) -> str | None:
        """`committee` or `interview` if a committee or interview in progress cites the posting
        (models only: no feature import), otherwise `None`."""
        for kind, model in (("committee", CommitteeRun), ("interview", Interview)):
            stmt = (
                select(model.id)
                .where(
                    model.user_id == self.user_id,
                    model.posting_id == posting_id,
                    model.status == "running",
                )
                .limit(1)
            )
            if (await self.session.execute(stmt)).scalar_one_or_none() is not None:
                return kind
        return None

    async def application_id(self, posting_id: str) -> str | None:
        """The application record that cites the posting, if it exists (model only: no feature
        import)."""
        stmt = (
            select(Application.id)
            .where(Application.user_id == self.user_id, Application.posting_id == posting_id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
