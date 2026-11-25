"""CV version ↔ application link (SPEC 6.1 no. 1, D139). A posting with a ready CV version and no
record gets its "To apply" record; as long as the record has not left "To apply", `cv_version_id`
follows the most recent ready version; on the first move out of "To apply" to any status except
"Withdrawn", it freezes the version sent (`version` event): a new version no longer replaces it,
even if the record goes back to "To apply" and then "Applied" again. Idempotent: a posting that
already has a record, whatever its status ("Withdrawn" included), does not get a second one.

A record without a posting (entered by hand or in one sentence) that looks like the posting
(`adopt_link`, D155) is **linked** instead of getting a second record: "To apply", it follows the
ready version; already applied, it freezes it ("linked to the record" event). A posting that looks
like an already linked record, or a "possible" one, gets no record: the alert on its page remains
the way. The CV (`cv`) never imports this module: the application reads the versions."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.repository import ApplicationRepository, EventRepository
from app.features.applications.service.adopt_link import link_posting, target_of
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.versions import ready_versions_by_posting
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import postings_by_ids
from app.features.postings.service.rules import company_key
from app.features.postings.service.runtime import utc_now

logger = logging.getLogger(__name__)

UNKNOWN_COMPANY = "Company not specified"
UNKNOWN_TITLE = "Position not specified"


def follows_version(row: Application) -> bool:
    """The record follows the most recent ready version: never applied."""
    return row.status == "to_apply" and row.applied_on is None


async def freeze_version(
    db: AsyncSession, user_id: str, row: Application, at: datetime, *, linked: bool = False
) -> None:
    """On the first move out of "To apply" (see `events`): the record keeps its posting's most
    recent ready version (`version` event); without a ready version, the one it was following.
    An already frozen version (`version` event) is never replaced. `linked`: the already applied
    record has just been linked to its posting, the version may postdate the application: the
    event says "linked to the record", not "sent"."""
    if row.posting_id is None or row.id in await EventRepository(db, user_id).version_frozen():
        return
    ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
    if ready is None:
        return
    row.cv_version_id = ready[0]
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="version",
        at=at,
        text=f"CV version {ready[1]} {'linked to the record' if linked else 'sent'}.",
        ref_id=ready[0],
    )


async def _link(
    db: AsyncSession, user_id: str, row: Application, posting: JobPosting, ready: tuple[str, int]
) -> None:
    """Links the record without a posting to the posting whose version is ready (see
    `adopt_link`): a "To apply" record follows the ready version, an already applied one freezes
    it."""
    link_posting(row, posting)
    if row.status not in ("to_apply", "withdrawn"):
        await freeze_version(db, user_id, row, utc_now(), linked=True)
    elif follows_version(row):
        row.cv_version_id = ready[0]
    logger.info("Record linked to a posting: user %s, record %s", user_id, row.id)


async def _create(db: AsyncSession, user_id: str, posting: JobPosting, version_id: str) -> None:
    analysis = posting.analysis or {}
    company = posting.company or analysis.get("company") or UNKNOWN_COMPANY
    row = await ApplicationRepository(db, user_id).add(
        posting_id=posting.id,
        company=company,
        company_norm=company_key(company),
        title=posting.title or analysis.get("title") or UNKNOWN_TITLE,
        url=posting.url,
        url_norm=posting.url_norm,
        posting_text=posting.text,
        status="to_apply",
        cv_version_id=version_id,
    )
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="created",
        at=utc_now(),
        status_to="to_apply",
        ref_id=version_id,
    )


async def adopt_versions(db: AsyncSession, user_id: str) -> int:
    """Creates the records of postings that have a ready version and no record, makes "To apply"
    records follow their version; returns the number of records created. The commit belongs to
    the caller, who holds the applications lock (`adopt`)."""
    ready = await ready_versions_by_posting(db, user_id)
    if not ready:
        return 0
    repo = ApplicationRepository(db, user_id)
    existing = await repo.by_postings(ready.keys())
    missing = [posting_id for posting_id in ready if posting_id not in existing]
    frozen = await EventRepository(db, user_id).version_frozen()
    for posting_id, row in existing.items():
        if (
            follows_version(row)
            and row.id not in frozen
            and row.cv_version_id != ready[posting_id][0]
        ):
            row.cv_version_id = ready[posting_id][0]
    postings = await postings_by_ids(db, user_id, missing)
    zone = await zone_of(db, user_id)
    today = local_today(zone, utc_now())
    rows = await repo.recent()
    created = 0
    for posting_id in missing:
        posting = postings.get(posting_id)
        if posting is None:
            continue
        target, similar = target_of(posting, rows, zone, today)
        if target is not None:
            await _link(db, user_id, target, posting, ready[posting_id])
        elif not similar:
            await _create(db, user_id, posting, ready[posting_id][0])
            created += 1
    await db.flush()
    if created:
        logger.info("Records created from CV versions: user %s, %d", user_id, created)
    return created


async def adopt(rt: ApplicationsRuntime, user_id: str) -> int:
    """`adopt_versions` under the applications lock, in its own (committed) transaction: called
    at the start of the list, the indicators and the scheduled job."""
    async with rt.lock(user_id), rt.session_factory() as db:
        created = await adopt_versions(db, user_id)
        await db.commit()
        return created
