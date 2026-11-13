"""Étapes du contrôle de fin de phase 5 contre une fausse API : une session morte ou déjà ouverte
est un échec clair, la leçon du bloc du jour est choisie, et l'attente a une fin."""

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_steps import Etude, _wait_finished, next_question, pick_program
from tests.scripts.phase4_fakes import api, fake_run

PROGRAMS = [{"id": "p1", "status": "validated"}]
LESSONS = [
    {"id": "l1", "module_id": "m1", "status": "pending"},
    {"id": "l2", "module_id": "m2", "status": "ready"},
    {"id": "l3", "module_id": "m3", "status": "ready"},
]


async def test_session_interrupted_is_a_clear_failure() -> None:
    routes = {
        "/study-sessions/s1": {"status": "interrupted"},
        "/sessions/a1": {"status": "failed", "error": {"code": "provider_error"}},
    }
    async with api(routes) as client:
        run = fake_run(client)
        state = Etude(study_id="s1", session_id="a1")
        with pytest.raises(CheckFailed, match="interrupted.*failed, provider_error") as caught:
            await _wait_finished(run, state)

    assert caught.value.step == "session"


async def test_the_block_of_the_day_picks_the_lesson_and_its_reading_tasks() -> None:
    block = {
        "lesson_id": "l3",
        "tasks": [
            {"title": "Lire 1", "type": "lire"},
            {"title": "Pratiquer", "type": "pratiquer"},
            {"title": "Regarder", "type": "regarder"},
        ],
    }
    routes = {
        "/programs": PROGRAMS,
        "/programs/p1/lessons": LESSONS,
        "/study-sessions/summary": {"open_session_id": None, "block": block},
    }
    async with api(routes) as client:
        run, state = fake_run(client), Etude()
        await pick_program(run, state)

    assert state.lessons == {"l2": "m2", "l3": "m3"}
    assert (state.lesson_id, state.module_id) == ("l3", "m3")
    assert state.reading == {"Lire 1", "Regarder"}
    assert run.program_id == "p1"


async def test_without_a_block_the_first_ready_lesson_is_taken() -> None:
    routes = {
        "/programs": PROGRAMS,
        "/programs/p1/lessons": LESSONS,
        "/study-sessions/summary": {"open_session_id": None, "block": None},
    }
    async with api(routes) as client:
        state = Etude()
        await pick_program(fake_run(client), state)

    assert state.lesson_id == "l2"
    assert state.reading == set()


async def test_an_open_study_session_stops_the_check() -> None:
    routes = {
        "/programs": PROGRAMS,
        "/programs/p1/lessons": LESSONS,
        "/study-sessions/summary": {"open_session_id": "s9", "block": None},
    }
    async with api(routes) as client:
        with pytest.raises(CheckFailed, match=r"déjà ouverte \(s9\)"):
            await pick_program(fake_run(client), Etude())


async def test_a_draft_program_has_no_lesson_to_study() -> None:
    routes = {"/programs": [{"id": "p1", "status": "draft"}]}
    async with api(routes) as client:
        with pytest.raises(CheckFailed, match="check_phase4"):
            await pick_program(fake_run(client), Etude())


async def test_waiting_for_a_question_has_an_end() -> None:
    routes = {"/sessions/a1": {"status": "running", "pending_interrupt": None}}
    async with api(routes) as client:
        with pytest.raises(CheckFailed, match="Délai dépassé"):
            await next_question(fake_run(client, timeout_s=0.5), "session", "a1", set())


async def test_a_dead_agent_session_is_not_waited_for() -> None:
    routes = {"/sessions/a1": {"status": "failed", "error": {"code": "provider_error"}}}
    async with api(routes) as client:
        with pytest.raises(CheckFailed, match=r"arrêtée \(failed, provider_error\)"):
            await next_question(fake_run(client), "session", "a1", set())
