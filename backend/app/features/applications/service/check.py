"""Check when a posting comes in (SPEC 6.3, D139): the incoming posting (an analyzed posting, a
link only) is compared with the existing records, whatever the screen. The rules are those of
`matching` (7.1); here, reading the posting and the records."""

from collections.abc import Iterable
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.applications.repository import ApplicationRepository
from app.features.applications.schemas import ApplicationRef, CheckOut
from app.features.applications.service.matching import Hit, Incoming, match
from app.features.applications.service.views import alerts_out, invalid, views_of
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import get_posting
from app.features.postings.service.rules import company_key, posting_url_key


def incoming_from_posting(posting: JobPosting, distinct: Iterable[str] = ()) -> Incoming:
    """The incoming posting: normalized link, company and job title (the posting's, otherwise
    the analysis'), "possible" postings among its duplicates, records confirmed as "another
    position"."""
    analysis = posting.analysis or {}
    return Incoming(
        url_norm=posting.url_norm,
        company_norm=company_key(posting.company or analysis.get("company") or ""),
        title=posting.title or analysis.get("title") or "",
        posting_id=posting.id,
        possible_posting_ids=frozenset(
            str(item["posting_id"])
            for item in posting.duplicates
            if isinstance(item, dict) and item.get("level") == "possible" and item.get("posting_id")
        ),
        distinct_from=frozenset(distinct),
    )


def incoming_from_url(url: str) -> Incoming:
    """Before analysis: only the link is known. 422 `url` if the link is rejected."""
    try:
        key = posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise invalid("url") from None
        raise
    return Incoming(
        url_norm=key,
        company_norm="",
        title="",
        posting_id=None,
        possible_posting_ids=frozenset(),
    )


async def check_incoming(
    db: AsyncSession, user_id: str, incoming: Incoming, today: date
) -> list[Hit]:
    """The records that look like the incoming posting (see `matching.match`)."""
    views = await views_of(db, user_id, await zone_of(db, user_id))
    return match(incoming, views, today)


async def check_posting(
    db: AsyncSession, user_id: str, now: datetime, posting_id: str | None, url: str | None
) -> CheckOut:
    """`GET /applications/check`: by `posting_id` (the posting's record, the alerts and the
    information) or by `url` (before analysis: the "certain" level only). Exactly one of the two
    inputs, otherwise 422."""
    if (posting_id is None) == (url is None):
        raise invalid("posting_id", "url")
    zone = await zone_of(db, user_id)
    today = local_today(zone, now)
    own = None
    if posting_id is not None:
        posting = await get_posting(db, user_id, posting_id)
        hits = await check_incoming(db, user_id, incoming_from_posting(posting), today)
        row = await ApplicationRepository(db, user_id).by_posting(posting_id)
        if row is not None:
            own = ApplicationRef.model_validate(row, from_attributes=True)
    else:
        assert url is not None
        found = await check_incoming(db, user_id, incoming_from_url(url), today)
        hits = [hit for hit in found if hit.level == "certain"]
    alerts = await alerts_out(db, user_id, hits, zone, today)
    return CheckOut(
        own=own,
        alerts=[a for a in alerts if a.level != "info"],
        info=[a for a in alerts if a.level == "info"],
    )
