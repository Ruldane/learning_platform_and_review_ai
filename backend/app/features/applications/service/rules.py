"""Pure application rules (SPEC 6.1, 6.4, D138): the order of statuses, what a status change
sets as dates, the indicators. No database: the service builds `ApplicationView` objects (7.2)
and passes them here."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import get_args

from app.db.models.applications import ApplicationStatus

# Kanban column order (SPEC 6.1), from To apply to Withdrawn.
STATUS_ORDER: tuple[ApplicationStatus, ...] = get_args(ApplicationStatus)
STATUS_LABELS: dict[ApplicationStatus, str] = {
    "to_apply": "To apply",
    "applied": "Applied",
    "followed_up": "Followed up",
    "interview": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "no_answer": "No answer",
    "withdrawn": "Withdrawn",
}
ANSWERED: frozenset[ApplicationStatus] = frozenset({"interview", "offer", "rejected"})
WAITING: frozenset[ApplicationStatus] = frozenset({"applied", "followed_up"})


@dataclass(frozen=True)
class ApplicationView:
    """What the rules read from a record: never the database row."""

    id: str
    status: ApplicationStatus
    company_norm: str
    title: str
    url_norm: str | None
    posting_id: str | None
    applied_on: date | None
    interview_on: date | None
    answered_on: date | None
    created_on: date
    distinct_from: frozenset[str] = frozenset()


@dataclass(frozen=True)
class StatusEffects:
    """The dates a status change sets (`None`: the field does not change)."""

    applied_on: date | None = None
    interview_on: date | None = None
    answered_on: date | None = None

    def fields(self) -> dict[str, date]:
        """The fields set, column name → date."""
        values = {
            "applied_on": self.applied_on,
            "interview_on": self.interview_on,
            "answered_on": self.answered_on,
        }
        return {name: value for name, value in values.items() if value is not None}


@dataclass(frozen=True)
class Stats:
    by_status: dict[ApplicationStatus, int]
    response_rate: float | None  # answered / applied; `None` without an applied record
    mean_response_days: float | None  # `None` without an answer
    due: int  # relances dues


def on_status(app: ApplicationView, new: ApplicationStatus, day: date) -> StatusEffects:
    """The dates set when `app` moves to `new` on day `day`: the application date at
    "Applied" (once), the interview date at "Interview" (if January gave none), the first
    answer date at the first entry into `ANSWERED` (it no longer moves). Any status is
    allowed, including a return to "To apply" (January corrects): no date is cleared then."""
    return StatusEffects(
        applied_on=day if new == "applied" and app.applied_on is None else None,
        interview_on=day if new == "interview" and app.interview_on is None else None,
        answered_on=day if new in ANSWERED and app.answered_on is None else None,
    )


def stats(apps: Sequence[ApplicationView], due_reminders: int) -> Stats:
    """The indicators (SPEC 6.4): records by status (all eight, zeros included), response rate
    (answered / applied; a record is applied when `applied_on` is set), average response time
    in days (rounded to 0.1) and reminders due."""
    by_status: dict[ApplicationStatus, int] = dict.fromkeys(STATUS_ORDER, 0)
    for app in apps:
        by_status[app.status] += 1
    delays = [
        (app.answered_on - app.applied_on).days
        for app in apps
        if app.applied_on is not None and app.answered_on is not None
    ]
    applied = sum(1 for app in apps if app.applied_on is not None)
    return Stats(
        by_status=by_status,
        response_rate=len(delays) / applied if applied else None,
        mean_response_days=round(sum(delays) / len(delays), 1) if delays else None,
        due=due_reminders,
    )
