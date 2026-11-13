"""Étapes « tout » du contrôle de fin de phase 5 contre une fausse API qui note les appels : les
bonnes réponses lues au second passage du quiz, le bilan hebdomadaire (calendrier, bilan déjà
écrit, réglages remis), une question inattendue et une replanification sans proposition."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from scripts import phase5_weekly
from scripts.phase4_rules import CheckFailed
from scripts.phase5_drive import drive
from scripts.phase5_weekly import weekly_review
from tests.scripts.phase5_fakes import FakeApi, etude

PARIS = ZoneInfo("Europe/Paris")


# --- Bilan hebdomadaire -------------------------------------------------------------------------

SETTINGS = {"timezone": "Europe/Paris", "weekly_review": {"day": "sunday", "time": "18:00"}}
WEEKS = {"weeks": [{"start_date": "2026-11-16"}, {"start_date": "2026-11-23"}]}


def weekly_api(over: dict[tuple[str, str], Any] | None = None) -> FakeApi:
    routes: dict[tuple[str, str], Any] = {
        ("GET", "/settings"): SETTINGS,
        ("PUT", "/settings"): SETTINGS,
        ("GET", "/programs/p1"): WEEKS,
        ("GET", "/journal"): {"entries": [], "next_before": None},
        ("GET", "/sessions"): [],
    }
    return FakeApi(routes | (over or {}))


def at(monkeypatch: pytest.MonkeyPatch, moment: datetime) -> None:
    monkeypatch.setattr(phase5_weekly, "local_now", lambda zone: moment)
    monkeypatch.setattr(phase5_weekly, "POLL_WEEKLY_S", 0.01)


async def test_a_review_the_calendar_cannot_write_is_refused_before_touching_the_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 13, 10, 0, tzinfo=PARIS))  # avant le programme
    api = weekly_api()
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="commence le 2026-11-16.*2026-11-22") as caught:
            await weekly_review(run, etude())

    assert caught.value.step == "bilan hebdomadaire"
    assert api.sent("PUT", "/settings") == []


async def test_a_review_already_written_today_is_not_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    today = {"entries": [{"id": "r0", "occurred_on": "2026-11-22"}], "next_before": None}
    session = {"id": "s0", "subject_id": "p1", "created_at": "2026-11-22T17:05:00Z"}
    api = weekly_api({("GET", "/journal"): today, ("GET", "/sessions"): [session]})
    client, run = api.run()
    async with client:
        state = etude()
        await weekly_review(run, state)

    assert state.review_entry_id is None
    assert api.sent("PUT", "/settings") == []


async def test_a_review_already_written_without_any_replan_session_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    today = {"entries": [{"id": "r0", "occurred_on": "2026-11-22"}], "next_before": None}
    api = weekly_api({("GET", "/journal"): today})
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="aucune session `replan`"):
            await weekly_review(run, etude())


async def test_the_settings_come_back_even_when_the_review_never_comes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    monkeypatch.setattr(phase5_weekly, "WEEKLY_LAUNCH_S", 0.05)
    api = weekly_api()
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Aucune entrée en 0 s"):
            await weekly_review(run, etude())

    puts = api.sent("PUT", "/settings")
    assert [p["weekly_review"] for p in puts] == [
        {"day": "sunday", "time": "18:29"},  # un jour local, l'heure moins une minute
        {"day": "sunday", "time": "18:00"},  # remis comme avant
    ]


# --- Sessions d'agents --------------------------------------------------------------------------


def waiting(kind: str) -> dict[str, Any]:
    return {"status": "waiting_user", "pending_interrupt": {"interrupt_id": "i1", "kind": kind}}


async def test_a_question_nobody_expected_stops_the_session_driver() -> None:
    api = FakeApi({("GET", "/sessions/s1"): waiting("capture_task")})
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Question « capture_task » inattendue"):
            await drive(run, "capture", "s1", {"capture_text": lambda question: "x"})


async def test_a_replan_left_open_is_cancelled_before_the_review_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    monkeypatch.setattr(phase5_weekly, "WEEKLY_LAUNCH_S", 0.05)
    old = {"id": "old", "subject_id": "p1", "status": "waiting_user", "created_at": "x"}
    api = weekly_api({("GET", "/sessions"): [old], ("POST", "/sessions/old/cancel"): {}})
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Aucune entrée"):
            await weekly_review(run, etude())

    steps = [(m, p) for m, p, _ in api.calls if p == "/sessions/old/cancel" or m == "PUT"]
    assert steps[0] == ("POST", "/sessions/old/cancel")  # avant le réglage de l'heure
