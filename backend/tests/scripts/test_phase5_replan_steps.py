"""Étape « replanification » du contrôle de fin de phase 5 contre une fausse API : une session qui
finit sans proposition dit la dernière version, un plan qui tient déjà (version `empty`) est
accepté s'il est vraiment sous le plafond, une replanification laissée ouverte est annulée."""

from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_replan import replan_week
from tests.scripts.phase5_fakes import FakeApi, etude

SETTINGS = {"timezone": "Europe/Paris"}


def program(load: int = 200) -> dict[str, Any]:
    week = {"rank": 1, "start_date": "2026-11-16", "load_minutes": load, "modules": []}
    return {"version": 2, "weeks": [week]}


def replan_api(
    status: str, *, load: int = 200, sessions: list[dict[str, Any]] | None = None
) -> FakeApi:
    return FakeApi(
        {
            ("GET", "/settings"): SETTINGS,
            ("GET", "/programs/p1"): program(load),
            ("GET", "/sessions"): sessions or [],
            ("POST", "/sessions/old/cancel"): {},
            ("POST", "/programs/p1/replan"): {"session_id": "s1"},
            ("GET", "/sessions/s1"): {"status": "completed", "pending_interrupt": None},
            ("GET", "/programs/p1/versions"): [
                {"version": 3, "status": status, "session_id": "s1"}
            ],
        }
    )


async def test_a_replan_that_ends_without_a_proposal_names_the_last_version() -> None:
    api = replan_api("impossible")
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="dernière version : 3 impossible"):
            await replan_week(run, etude())

    assert api.sent("POST", "/programs/p1/replan") == [
        {"available_minutes": 300, "message": "cette semaine je n'ai que 5 heures"}
    ]


async def test_a_plan_that_already_fits_is_nothing_to_change() -> None:
    api = replan_api("empty", load=255)
    client, run = api.run()
    async with client:
        await replan_week(run, etude())

    assert api.sent("POST", "/sessions/s1/resume") == []  # rien à accepter


async def test_nothing_to_change_over_the_cap_is_a_failure() -> None:
    api = replan_api("empty", load=256)
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Rien à changer, mais la semaine 1 compte 256"):
            await replan_week(run, etude())


async def test_a_replan_left_open_by_an_interrupted_run_is_cancelled_first() -> None:
    sessions = [
        {"id": "old", "subject_id": "p1", "status": "waiting_user"},
        {"id": "done", "subject_id": "p1", "status": "completed"},
        {"id": "other", "subject_id": "p2", "status": "running"},
    ]
    api = replan_api("empty", sessions=sessions)
    client, run = api.run()
    async with client:
        await replan_week(run, etude())

    cancelled = [path for method, path, _ in api.calls if path.endswith("/cancel")]
    assert cancelled == ["/sessions/old/cancel"]
    order = [
        path for _, path, _ in api.calls if path in ("/sessions/old/cancel", "/programs/p1/replan")
    ]
    assert order == ["/sessions/old/cancel", "/programs/p1/replan"]
