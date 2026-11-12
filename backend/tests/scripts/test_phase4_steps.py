"""Étapes du contrôle de fin de phase 4 contre une fausse API : le programme et les leçons des
semaines 1 et 2 sont vraiment exigés (chaque module, son PDF), et l'attente a une fin."""

from typing import Any

import httpx
import pytest

from scripts.phase4_steps import CheckFailed, check_lessons, check_program
from tests.scripts.phase4_fakes import api, fake_run, lesson, program, week

PENDING = {"status": "waiting_user", "pending_interrupt": {"kind": "validate_program"}}
GOAL = {"program_id": "p1", "program_session_id": "s2"}
FILES = {"/pdf": httpx.Response(200, content=b"%PDF-1.4"), "": {"resources": [1, 2, 3, 4]}}


def two_modules(rank: int) -> dict[str, Any]:
    first, second = week(rank, module=f"m{rank}a"), week(rank, module=f"m{rank}b")
    first["modules"] += second["modules"]
    return first


async def _program(found: dict[str, object]) -> dict[str, int]:
    routes = {"/goals/g1": GOAL, "/sessions/s2": PENDING, "/programs/p1": found}
    async with api(routes) as client:
        run = fake_run(client)
        await check_program(run)
        return run.lesson_modules


async def test_program_keeps_every_module_of_weeks_one_and_two() -> None:
    modules = await _program(program(two_modules(1), two_modules(2), week(3)))

    assert modules == {"m1a": 1, "m1b": 1, "m2a": 2, "m2b": 2}


@pytest.mark.parametrize(
    ("found", "message"),
    [
        (program(week(1)), "moins de 2 semaines"),
        (program(week(2), week(3)), "moins de 2 semaines"),
        (program(week(1), week(2), status="validated"), "sans brouillon"),
        (program(week(1), week(2, load=500)), "semaine 2 : 500 min pour 400"),
        (program(week(1, practice="lire"), week(2)), "semaine 1 sans pratique"),
        (program(week(1), week(2, quiz="lire")), "semaine 2 ne finit pas par un quiz"),
    ],
)
async def test_program_fails_when_a_rule_is_broken(found: dict[str, object], message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        await _program(found)
    assert caught.value.step == "programme"


async def _lessons(
    listed: object, files: dict[str, object] = FILES, timeout_s: float = 1.0
) -> None:
    routes = {"/programs/p1/lessons": listed, **files}
    async with api(routes) as client:
        run = fake_run(client, timeout_s=timeout_s)
        run.lesson_modules = {"m1a": 1, "m1b": 1, "m2a": 2}
        await check_lessons(run)


async def test_lessons_pass_when_every_module_has_its_pdf() -> None:
    await _lessons([lesson("m1a"), lesson("m1b"), lesson("m2a"), lesson("m9", "failed")])


@pytest.mark.parametrize(
    "listed",
    [
        [],  # aucune leçon : `all([])` ne suffit plus
        [lesson("m1a"), lesson("m2a")],  # le second module de la semaine 1 manque
        [lesson("m1a"), lesson("m1b"), lesson("m2a", pdf=False)],  # PDF pas encore rendu
        [lesson("m1a"), lesson("m1b"), lesson("m2a", "generating")],
    ],
)
async def test_lessons_wait_until_the_deadline(listed: object) -> None:
    with pytest.raises(CheckFailed, match="Délai dépassé") as caught:
        await _lessons(listed, timeout_s=0.3)
    assert caught.value.step == "leçons"


async def test_a_failed_lesson_stops_the_check_at_once() -> None:
    with pytest.raises(CheckFailed, match="en échec : l-m1b"):
        await _lessons([lesson("m1a"), lesson("m1b", "failed")], timeout_s=60)


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({"/pdf": httpx.Response(200, content=b"<html>"), "": {"resources": [1, 2, 3]}}, "PDF"),
        ({"/pdf": httpx.Response(200, content=b"%PDF"), "": {"resources": [1, 2]}}, "2 ress"),
        ({"/pdf": httpx.Response(200, content=b"%PDF"), "": {"resources": [0] * 7}}, "7 ress"),
        ({"/pdf": httpx.Response(404, json={"error": {"code": "lesson_pdf_missing"}})}, "404"),
    ],
)
async def test_lesson_files_are_checked(files: dict[str, object], message: str) -> None:
    listed = [lesson("m1a"), lesson("m1b"), lesson("m2a")]
    with pytest.raises(CheckFailed, match=message) as caught:
        await _lessons(listed, files)
    assert caught.value.step == "leçons"
