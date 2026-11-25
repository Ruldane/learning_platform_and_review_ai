"""Reminder deadlines (SPEC 6.2, D138): which reminders a record is waiting for, and on which
day. Pure functions: the service (7.3) compares this result with the recorded reminders."""

from dataclasses import dataclass
from datetime import date, timedelta

from app.db.models.applications import ReminderKind
from app.features.applications.service.rules import WAITING, ApplicationView
from app.features.settings.service import DEFAULT_DELAYS as DEFAULT_DELAYS
from app.features.settings.service import validated_delays as validated_delays

POST_INTERVIEW = (1, 7)  # next day: thank-you; 7 days: request for news (fixed, 6.2)
WAITING_KINDS: tuple[ReminderKind, ...] = ("linkedin_7", "email_14", "close_21")
INTERVIEW_KINDS: tuple[ReminderKind, ...] = ("thanks", "news_7")


@dataclass(frozen=True)
class Expected:
    """An expected reminder: `anchor_on` is the date it stems from (application or interview),
    `due_on` its deadline."""

    kind: ReminderKind
    anchor_on: date
    due_on: date


def expected_reminders(app: ApplicationView, delays: tuple[int, int, int]) -> list[Expected]:
    """The reminders `app` is waiting for: while awaiting a reply ("Applied" or "Followed up",
    with its application date): LinkedIn, email and ranking at the `delays`; at "Interview",
    with its interview date: a thank-you the next day and a request for news 7 days later;
    otherwise none (a reply removes the waiting reminders)."""
    if app.status in WAITING and app.applied_on is not None:
        anchor = app.applied_on
        return [
            Expected(kind, anchor, anchor + timedelta(days=days))
            for kind, days in zip(WAITING_KINDS, delays, strict=True)
        ]
    if app.status == "interview" and app.interview_on is not None:
        anchor = app.interview_on
        return [
            Expected(kind, anchor, anchor + timedelta(days=days))
            for kind, days in zip(INTERVIEW_KINDS, POST_INTERVIEW, strict=True)
        ]
    return []
