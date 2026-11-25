"""Creating a record (SPEC 6.1 no. 2, 6.3, D139), by hand or from a posting, under the lock of
the user's applications: duplicate check, then writing the record, its timeline and its
contacts in the same transaction.

- A record for this posting already exists: 409 `application_exists` (`details.application_id`).
- A record that looks alike (certain, probable, possible) and that `distinct_from` does not
  cover: 409 `application_duplicate` (`details.alerts`: the existing records, never the input).
- Otherwise 201; records of the same company from the last 30 days go out as `info`, and
  `distinct_from` is set in both directions (with the posting of each record, so that the
  per-posting check goes quiet too).

Created by a session of the tracking assistant (`session_id`, 7.4), the record keeps the session
id in `ref_id` of its `created` event: a creation replayed after a stop (SPEC 9.4) re-reads that
record instead of creating a second one.

Logs: ids only, never the company, the title, a contact or a note."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.repository import (
    ApplicationRepository,
    ContactRepository,
    EventRepository,
)
from app.features.applications.schemas import AlertOut, CreatedOut
from app.features.applications.schemas import ApplicationIn as ApplicationIn
from app.features.applications.service.adopt import follows_version, freeze_version
from app.features.applications.service.check import incoming_from_posting
from app.features.applications.service.matching import Incoming, match
from app.features.applications.service.reminder_sync import sync_user
from app.features.applications.service.rules import ApplicationView, on_status
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import alerts_out, detail_out, invalid, view_of
from app.features.cv.service.versions import ready_versions_by_posting
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import get_posting
from app.features.postings.service.rules import company_key, posting_url_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    """What goes into the record: the frozen copy of the posting or what January typed."""

    posting_id: str | None
    company: str
    title: str
    url: str | None
    url_norm: str | None
    text: str | None


def application_exists(application_id: str) -> AppError:
    return AppError(
        "application_exists",
        "An application already exists for this posting.",
        409,
        {"application_id": application_id},
    )


def application_duplicate(alerts: list[AlertOut]) -> AppError:
    return AppError(
        "application_duplicate",
        "This posting is similar to an existing application.",
        409,
        {"alerts": [alert.model_dump(mode="json") for alert in alerts]},
    )


def link_key(url: str | None) -> str | None:
    """The link key; 422 `url` if it is refused (never quoted)."""
    if url is None:
        return None
    try:
        return posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise invalid("url") from None
        raise


def _source(body: ApplicationIn, posting: JobPosting | None) -> Source:
    """The frozen copy of the posting (company, title, link, text); what January typed only
    serves where the posting says nothing yet. Without `company` or `title`: 422 `fields`."""
    analysis = (posting.analysis if posting is not None else None) or {}
    company = (posting.company if posting else None) or analysis.get("company") or body.company
    title = (posting.title if posting else None) or analysis.get("title") or body.title
    missing = [name for name, value in (("company", company), ("title", title)) if not value]
    if missing or company is None or title is None:
        raise invalid(*missing)
    url = (posting.url if posting else None) or body.url
    url_norm = (posting.url_norm if posting else None) or link_key(url)
    text = posting.text if posting else body.posting_text
    return Source(posting.id if posting else None, company, title, url, url_norm, text or None)


def _incoming(source: Source, posting: JobPosting | None, body: ApplicationIn) -> Incoming:
    """The incoming posting, as the record will be written (`source`: company, title, link,
    including what January typed for a posting not yet analyzed); of the posting, only the id
    and its "possible" postings count."""
    possible = incoming_from_posting(posting).possible_posting_ids if posting else frozenset()
    return Incoming(
        url_norm=source.url_norm,
        company_norm=company_key(source.company),
        title=source.title,
        posting_id=source.posting_id,
        possible_posting_ids=possible,
        distinct_from=frozenset(body.distinct_from),
    )


def _dates(body: ApplicationIn, source: Source, today: date) -> dict[str, date]:
    """The dates set by the starting status (`on_status`); the given application date wins
    over today's."""
    start = ApplicationView(
        id="",
        status="to_apply",
        company_norm="",
        title=source.title,
        url_norm=None,
        posting_id=None,
        applied_on=body.applied_on,
        interview_on=None,
        answered_on=None,
        created_on=today,
    )
    fields = on_status(start, body.status, today).fields()
    if body.applied_on is not None:
        fields["applied_on"] = body.applied_on
    return fields


def _joined(current: list[object], rows: list[Application]) -> list[object]:
    merged = list(current)
    for row in rows:
        for value in (row.id, row.posting_id):
            if value is not None and value not in merged:
                merged.append(value)
    return merged


def confirm_distinct(rows: list[Application], new: Application, confirmed: list[str]) -> None:
    """ "It is another job": each confirmed record and the new one point at each other, by
    record id and by posting (the per-posting check goes quiet too)."""
    others = [row for row in rows if row.id in confirmed]
    new.distinct_from = _joined(new.distinct_from, others)
    for other in others:
        other.distinct_from = _joined(other.distinct_from, [new])


async def _link_version(db: AsyncSession, user_id: str, row: Application, now: datetime) -> None:
    """A "To apply" record follows the ready version of its posting; a record created at a
    status other than "Withdrawn" freezes it (the sent version is today's)."""
    if row.posting_id is None:
        return
    if row.status not in ("to_apply", "withdrawn"):
        await freeze_version(db, user_id, row, now)
    elif follows_version(row):
        ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
        row.cv_version_id = ready[0] if ready else None


async def _insert(
    db: AsyncSession,
    user_id: str,
    body: ApplicationIn,
    source: Source,
    when: tuple[date, datetime],
    session_id: str | None,
) -> Application:
    today, now = when
    row = await ApplicationRepository(db, user_id).add(
        posting_id=source.posting_id,
        company=source.company,
        company_norm=company_key(source.company),
        title=source.title,
        url=source.url,
        url_norm=source.url_norm,
        posting_text=source.text,
        channel=body.channel,
        status=body.status,
        notes=body.notes,
        **_dates(body, source, today),
    )
    await EventRepository(db, user_id).add(
        application_id=row.id, kind="created", at=now, status_to=body.status, ref_id=session_id
    )
    await _link_version(db, user_id, row, now)
    contacts = ContactRepository(db, user_id)
    for contact in body.contacts:
        await contacts.add(
            application_id=row.id, name=contact.name, role=contact.role, url=contact.url
        )
    return row


async def _of_session(
    db: AsyncSession, user_id: str, session_id: str | None, today: date
) -> CreatedOut | None:
    """The record already created by this session (replay), otherwise `None`."""
    if session_id is None:
        return None
    known = await EventRepository(db, user_id).created_by(session_id)
    if known is None:
        return None
    row = await ApplicationRepository(db, user_id).get_fresh(known)
    return (
        None
        if row is None
        else CreatedOut(application=await detail_out(db, user_id, row, today), info=[])
    )


async def create_application(
    rt: ApplicationsRuntime, user_id: str, body: ApplicationIn, *, session_id: str | None = None
) -> CreatedOut:
    """Creates the record (see the module). 404 `posting_not_found` if `posting_id` is unknown."""
    async with rt.lock(user_id), rt.session_factory() as db:
        zone = await zone_of(db, user_id)
        now = rt.now()
        today = local_today(zone, now)
        if (again := await _of_session(db, user_id, session_id, today)) is not None:
            return again
        repo = ApplicationRepository(db, user_id)
        posting = await get_posting(db, user_id, body.posting_id) if body.posting_id else None
        if posting is not None and (known := await repo.by_posting(posting.id)) is not None:
            raise application_exists(known.id)
        source = _source(body, posting)
        rows = await repo.recent()
        hits = match(_incoming(source, posting, body), [view_of(r, zone) for r in rows], today)
        blocking = [hit for hit in hits if hit.level != "info"]
        if blocking:
            raise application_duplicate(await alerts_out(db, user_id, blocking, zone, today))
        row = await _insert(db, user_id, body, source, (today, now), session_id)
        confirm_distinct(rows, row, list(dict.fromkeys(body.distinct_from)))
        await sync_user(db, user_id, today, application_id=row.id)
        await db.commit()
        info = [hit for hit in hits if hit.level == "info"]
        logger.info("Record created: user %s, record %s", user_id, row.id)
        return CreatedOut(
            application=await detail_out(db, user_id, row, today),
            info=await alerts_out(db, user_id, info, zone, today),
        )
