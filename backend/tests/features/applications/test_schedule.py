"""Échéances des relances (7.1)."""

from datetime import date

import pytest

from app.db.models.applications import ApplicationStatus
from app.features.applications.service.rules import ApplicationView
from app.features.applications.service.schedule import (
    Expected,
    expected_reminders,
    validated_delays,
)


def d(day: int, month: int = 11) -> date:
    return date(2026, month, day)


def view(
    status: ApplicationStatus, *, applied: date | None = None, interview: date | None = None
) -> ApplicationView:
    return ApplicationView(
        id="a1",
        status=status,
        company_norm="societe fictive",
        title="Développeuse IA",
        url_norm=None,
        posting_id=None,
        applied_on=applied,
        interview_on=interview,
        answered_on=None,
        created_on=d(1),
        distinct_from=frozenset(),
    )


def test_expected_waiting_reminders() -> None:
    expected = expected_reminders(view("applied", applied=d(1)), (7, 14, 21))
    assert expected == [
        Expected("linkedin_7", d(1), d(8)),
        Expected("email_14", d(1), d(15)),
        Expected("close_21", d(1), d(22)),
    ]
    assert expected_reminders(view("followed_up", applied=d(1)), (7, 14, 21)) == expected


@pytest.mark.parametrize("status", ["rejected", "offer", "no_answer", "withdrawn", "to_apply"])
def test_answer_removes_pending_followups(status: ApplicationStatus) -> None:
    assert expected_reminders(view(status, applied=d(1)), (7, 14, 21)) == []


def test_waiting_without_applied_date_expects_nothing() -> None:
    assert expected_reminders(view("applied"), (7, 14, 21)) == []


def test_interview_reminders() -> None:
    expected = expected_reminders(view("interview", applied=d(1), interview=d(10)), (7, 14, 21))
    assert expected == [Expected("thanks", d(10), d(11)), Expected("news_7", d(10), d(17))]
    assert expected_reminders(view("interview", applied=d(1)), (7, 14, 21)) == []


def test_changed_delays_move_pending_only() -> None:
    expected = expected_reminders(view("applied", applied=d(1)), (5, 10, 15))
    assert [e.due_on for e in expected] == [d(6), d(11), d(16)]
    assert {e.anchor_on for e in expected} == {d(1)}  # la même ancre : les relances se déplacent


def test_valid_delays_are_kept() -> None:
    assert validated_delays([5, 10, 15]) == (5, 10, 15)
    assert validated_delays([1, 2, 90]) == (1, 2, 90)


@pytest.mark.parametrize(
    "raw", [(14, 7, 21), (0, 7, 14), (7, 14), (7, 7, 21), (7, 14, 91), (1, 2, 3, 4), (), (-1, 5, 9)]
)
def test_invalid_delays_fall_back(raw: tuple[int, ...]) -> None:
    assert validated_delays(raw) == (7, 14, 21)


def test_boolean_delays_are_invalid() -> None:
    assert validated_delays([True, 2, 3]) == (7, 14, 21)
