"""Gap reads (F8, D122): the offers whose attachment is stored, and the keywords that the CV
reviews sent to the gap (preflight G3). Every query filters by `user_id`."""

import builtins
from collections import defaultdict
from collections.abc import Collection

from sqlalchemy import literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.career import CvReview
from app.db.models.postings import JobPosting


class GapRepository:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def with_gap(self) -> builtins.list[JobPosting]:
        """The analysed offers whose attachment is stored (rejected ones excluded)."""
        stmt = (
            select(JobPosting)
            .where(
                JobPosting.user_id == self.user_id,
                JobPosting.gap.is_not(None),
                JobPosting.analysis.is_not(None),
                JobPosting.status != "rejected",
            )
            .order_by(JobPosting.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def ready_recent(self) -> builtins.list[JobPosting]:
        """The ready offers (analysed), most recent first."""
        stmt = (
            select(JobPosting)
            .where(
                JobPosting.user_id == self.user_id,
                JobPosting.status == "ready",
                JobPosting.analysis.is_not(None),
            )
            .order_by(JobPosting.created_at.desc(), literal_column("rowid").desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def review_terms(self, posting_ids: Collection[str]) -> dict[str, list[str]]:
        """`offer → terms` of the CV reviews of these offers, in review order."""
        if not posting_ids:
            return {}
        stmt = (
            select(CvReview.posting_id, CvReview.keywords_to_gap)
            .where(
                CvReview.user_id == self.user_id,
                CvReview.posting_id.in_(builtins.list(posting_ids)),
            )
            .order_by(CvReview.created_at, literal_column("rowid"))
        )
        terms: defaultdict[str, list[str]] = defaultdict(list)
        for posting_id, raw in (await self.session.execute(stmt)).all():
            terms[posting_id].extend(_term(item) for item in raw or [])
        return {key: [t for t in values if t] for key, values in terms.items()}


def _term(item: object) -> str:
    """A keyword stored by the review: the term alone, or `{"term": …}` (6.14 shape)."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("term") or "").strip()
    return ""
