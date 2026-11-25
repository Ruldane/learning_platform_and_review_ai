"""Duplicate applications (SPEC 6.3, D138): an incoming offer is compared with the existing
records, whatever the screen. Pure functions: the service (7.2) builds the `ApplicationView`
and the `Incoming`, the route returns the records found."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.core.clock import english_day
from app.db.models.applications import ApplicationStatus
from app.features.applications.service.rules import STATUS_LABELS, ApplicationView
from app.features.postings.service.rules import PROBABLE_TITLE, title_similarity

DuplicateLevel = Literal["certain", "probable", "possible"]
HitLevel = DuplicateLevel | Literal["info"]
INFO_DAYS = 30  # another record at the same company, within the last 30 days
_RANK: dict[HitLevel, int] = {"certain": 0, "probable": 1, "possible": 2, "info": 3}


@dataclass(frozen=True)
class Incoming:
    """The incoming offer: its normalized link, normalized company, title, posting identifier
    (if any), its "possible" offers (D121), and the identifiers (records or offers) that January
    has already confirmed as "other role" for it."""

    url_norm: str | None
    company_norm: str
    title: str
    posting_id: str | None
    possible_posting_ids: frozenset[str]
    distinct_from: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Hit:
    level: HitLevel
    application_id: str


def _reference_day(app: ApplicationView) -> date:
    return app.applied_on or app.created_on


def _is_distinct(incoming: Incoming, app: ApplicationView) -> bool:
    """January confirmed "other role" for this pair, in either direction."""
    if incoming.posting_id is not None and incoming.posting_id in app.distinct_from:
        return True
    return app.id in incoming.distinct_from or (
        app.posting_id is not None and app.posting_id in incoming.distinct_from
    )


def _level(incoming: Incoming, app: ApplicationView, today: date) -> HitLevel | None:
    if incoming.url_norm is not None and incoming.url_norm == app.url_norm:
        return "certain"
    if not incoming.company_norm or app.company_norm != incoming.company_norm:
        return None  # an empty key (a name with no Latin letter) designates no company
    if title_similarity(incoming.title, app.title) >= PROBABLE_TITLE:
        return "probable"
    if app.posting_id is not None and app.posting_id in incoming.possible_posting_ids:
        return "possible"
    return "info" if (today - _reference_day(app)).days <= INFO_DAYS else None


def match(incoming: Incoming, apps: Sequence[ApplicationView], today: date) -> list[Hit]:
    """The records that resemble the incoming offer, one level per record (the strongest):
    same link: certain; same company (non-empty key) and title at 85%: probable; same company
    and "possible" offer: possible; same company within the last 30 days: info.
    The record for the same offer (same `posting_id`) is never a duplicate, nor is a record
    confirmed as "other role". Sorted by level, then by application date (or creation date),
    newest first."""
    found: list[tuple[HitLevel, ApplicationView]] = []
    for app in apps:
        if incoming.posting_id is not None and incoming.posting_id == app.posting_id:
            continue
        if _is_distinct(incoming, app):
            continue
        level = _level(incoming, app, today)
        if level is not None:
            found.append((level, app))
    found.sort(key=lambda item: (_RANK[item[0]], -_reference_day(item[1]).toordinal(), item[1].id))
    return [Hit(level, app.id) for level, app in found]


def _ago(day: date | None, today: date) -> str:
    if day is None:
        return ""
    days = (today - day).days
    if days <= 0:
        return " today"
    return f" {days} day{'s' if days > 1 else ''} ago"


def alert_message(
    level: HitLevel,
    company: str,
    title: str,
    status: ApplicationStatus,
    day: date | None,
    today: date,
) -> str:
    """Describe an existing application or an informational match at the same company."""
    drafted = status == "to_apply"
    role = f"the {title} role at {company}"
    if level == "info":
        action = "added an application for" if drafted else "applied for"
        return f"For reference, you {action} {role}{_ago(day, today)}."
    when = f" on {english_day(day, include_year=day.year != today.year)}" if day else ""
    label = STATUS_LABELS[status]
    if drafted:
        created = f", created{when}" if when else ""
        return f"You already have an application for {role}{created} ({label})."
    return f"You already applied for {role}{when} ({label})."
