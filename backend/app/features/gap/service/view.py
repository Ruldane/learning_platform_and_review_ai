"""The gap of an offer as it is shown (`GET /postings/{id}/gap`, D122): status from the stored
session (`gap_status`), rows and score recalculated when it is ready."""

from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.postings import JobPosting
from app.features.gap.schemas import GapOut, GapRowOut
from app.features.gap.service.rows import gap_rows
from app.features.gap.service.score import match_score
from app.features.postings.service.queries import get_posting
from app.features.postings.service.status import gap_status, read_with_sessions


async def posting_gap(db: AsyncSession, user_id: str, posting_id: str) -> GapOut:
    """Another user's offer or a missing one: 404 `posting_not_found`."""

    async def read() -> JobPosting:
        return await get_posting(db, user_id, posting_id)

    posting, open_ids = await read_with_sessions(db, user_id, read, lambda p: [p])
    status = gap_status(posting, open_ids.get(posting.id, []))
    rows = await gap_rows(db, user_id, posting) if status == "ready" else []
    return GapOut(
        posting_id=posting.id,
        status=status,
        score=match_score(rows) if status == "ready" else None,
        rows=[GapRowOut(**asdict(row)) for row in rows],
        session_id=posting.gap_session_id,
    )
