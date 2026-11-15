"""Règles pures des candidatures (7.1) : changements de statut et indicateurs."""

from datetime import date

from app.db.models.applications import ApplicationStatus
from app.features.applications.service.rules import (
    ANSWERED,
    STATUS_ORDER,
    WAITING,
    ApplicationView,
    on_status,
    stats,
)


def d(day: int, month: int) -> date:
    return date(2026, month, day)


def view(
    status: ApplicationStatus = "to_apply",
    *,
    applied: date | None = None,
    interview: date | None = None,
    answered: date | None = None,
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
        answered_on=answered,
        created_on=d(1, 11),
        distinct_from=frozenset(),
    )


def applied(day: date, *, answered: date | None = None) -> ApplicationView:
    return view("interview" if answered else "applied", applied=day, answered=answered)


def to_apply() -> ApplicationView:
    return view()


def test_status_order_follows_the_kanban() -> None:
    assert STATUS_ORDER == (
        "to_apply",
        "applied",
        "followed_up",
        "interview",
        "offer",
        "rejected",
        "no_answer",
        "withdrawn",
    )
    assert {"interview", "offer", "rejected"} == ANSWERED
    assert {"applied", "followed_up"} == WAITING


def test_on_status_applied_sets_date_once() -> None:
    first = on_status(view(), "applied", d(3, 11))
    assert first.fields() == {"applied_on": d(3, 11)}
    again = on_status(view("to_apply", applied=d(3, 11)), "applied", d(9, 11))
    assert again.fields() == {}


def test_first_answer_sets_answered_on() -> None:
    first = on_status(view("applied", applied=d(1, 11)), "interview", d(8, 11))
    assert first.answered_on == d(8, 11) and first.interview_on == d(8, 11)
    # Entretien, puis refus : la première date de réponse reste.
    later = view("interview", applied=d(1, 11), interview=d(8, 11), answered=d(8, 11))
    assert on_status(later, "rejected", d(20, 11)).fields() == {}


def test_interview_keeps_a_date_january_gave() -> None:
    given = view("applied", applied=d(1, 11), interview=d(12, 11))
    assert on_status(given, "interview", d(8, 11)).fields() == {"answered_on": d(8, 11)}


def test_back_to_to_apply_sets_nothing() -> None:
    back = view("applied", applied=d(1, 11), answered=d(5, 11))
    assert on_status(back, "to_apply", d(9, 11)).fields() == {}


def test_stats_rates_and_delays() -> None:
    s = stats([applied(d(1, 11), answered=d(8, 11)), applied(d(3, 11)), to_apply()], 2)
    assert s.by_status["applied"] == 1 and s.response_rate == 0.5
    assert s.mean_response_days == 7.0 and s.due == 2
    assert len(s.by_status) == 8 and s.by_status["withdrawn"] == 0


def test_stats_mean_is_rounded_to_a_tenth() -> None:
    apps = [
        applied(d(1, 11), answered=d(4, 11)),
        applied(d(1, 11), answered=d(5, 11)),
        applied(d(1, 11), answered=d(5, 11)),
    ]
    assert stats(apps, 0).mean_response_days == 3.7


def test_stats_empty_is_none_not_zero_division() -> None:
    s = stats([], due_reminders=0)
    assert s.response_rate is None and s.mean_response_days is None
    assert sum(s.by_status.values()) == 0
    only_draft = stats([to_apply()], due_reminders=0)
    assert only_draft.response_rate is None and only_draft.mean_response_days is None
