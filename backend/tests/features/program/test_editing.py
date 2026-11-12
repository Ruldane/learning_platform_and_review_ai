"""Modifications de January (D88) : chaque semaine touchée garde 85 % du budget au plus, une
pratique et un quiz, même sous des requêtes simultanées ; une 422 ne recopie jamais la saisie."""

import asyncio
import logging
from typing import Any

import httpx
import pytest

from app.features.program.service import editing
from tests.features.program.conftest import Draft
from tests.features.program.support import (
    API,
    CAP,
    TUESDAY_W1,
    WEEK1_LOAD,
    WEEK2_LOAD,
    task_id,
    tasks_of,
    view,
    week_load,
)


@pytest.fixture
def slow_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chaque relecture du programme laisse la main un instant : sans le verrou du programme,
    deux requêtes liraient le même état et passeraient toutes deux la règle des 85 %."""
    real = editing.load

    async def slow(*args: Any) -> Any:
        loaded = await real(*args)
        await asyncio.sleep(0.05)
        return loaded

    monkeypatch.setattr(editing, "load", slow)


async def _move(client: httpx.AsyncClient, tid: str, day: str) -> httpx.Response:
    return await client.patch(f"{API}/tasks/{tid}", json={"planned_date": day})


async def test_move_task_within_budget(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire l'article A")  # 40 min, semaine 2
    r = await _move(client, tid, TUESDAY_W1)
    assert r.status_code == 200, r.text
    assert r.json()["planned_date"] == TUESDAY_W1
    after = await view(client, draft_program.program_id)
    assert week_load(after, 1) == WEEK1_LOAD + 40 <= CAP
    assert week_load(after, 2) == WEEK2_LOAD - 40


async def test_move_over_85_percent_is_422(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire l'article C")  # 60 min : 665 + 60 > 714
    r = await _move(client, tid, TUESDAY_W1)
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "week_over_budget"
    assert error["details"] == {"week_rank": 1, "planned_minutes": 725, "cap_minutes": CAP}
    assert "Lire l'article C" not in r.text
    assert week_load(await view(client, draft_program.program_id), 1) == WEEK1_LOAD


@pytest.mark.parametrize("attempt", range(3))
async def test_concurrent_moves_never_exceed_85_percent(
    client: httpx.AsyncClient, draft_program: Draft, slow_reads: None, attempt: int
) -> None:
    program = await view(client, draft_program.program_id)
    t1, t2 = task_id(program, "Lire l'article A"), task_id(program, "Lire l'article B")
    # Chacune tient seule (665 + 40 = 705), pas ensemble (745).
    first, second = await asyncio.gather(
        _move(client, t1, TUESDAY_W1), _move(client, t2, TUESDAY_W1)
    )
    codes = sorted([first.status_code, second.status_code])
    assert codes == [200, 422]
    refused = first if first.status_code == 422 else second
    assert refused.json()["error"]["code"] == "week_over_budget"
    assert "Lire l'article" not in refused.text
    assert week_load(await view(client, draft_program.program_id), 1) == WEEK1_LOAD + 40 <= CAP


async def test_add_task_over_budget_is_refused_without_echo(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    module_id = program["weeks"][0]["modules"][0]["id"]
    new = {
        "module_id": module_id,
        "title": "Titre-unique-xyz",
        "type": "lire",
        "minutes": 60,
        "done_criterion": "Critere-unique-abc",
        "planned_date": "2026-11-18",
    }
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json={"add_tasks": [new]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "week_over_budget"
    assert "Titre-unique-xyz" not in r.text and "Critere-unique-abc" not in r.text
    assert len(tasks_of(await view(client, draft_program.program_id))) == 12


async def test_add_task_within_budget(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    module_id = program["weeks"][1]["modules"][0]["id"]
    new = {
        "module_id": module_id,
        "title": "Relire les notes",
        "type": "lire",
        "minutes": 30,
        "done_criterion": "Notes relues",
        "planned_date": "2026-11-25",
    }
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json={"add_tasks": [new]})
    assert r.status_code == 200, r.text
    assert week_load(r.json(), 2) == WEEK2_LOAD + 30
    assert "Relire les notes" in [t["title"] for t in tasks_of(r.json())]


async def test_invalid_task_is_refused_without_echo(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    new = {"module_id": "m", "title": "Titre-unique-xyz", "type": "lire", "minutes": 200}
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json={"add_tasks": [new]})
    assert r.status_code == 422 and "Titre-unique-xyz" not in r.text


async def test_deleting_last_quiz_is_refused(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    quiz = task_id(program, "Faire le quiz 1")
    body = {"delete_task_ids": [quiz]}
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "week_needs_quiz"
    assert quiz in [t["id"] for t in tasks_of(await view(client, draft_program.program_id))]


async def test_moving_the_only_practice_out_is_refused(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    r = await _move(client, task_id(program, "Pratiquer le projet"), TUESDAY_W1)
    assert r.status_code == 422 and r.json()["error"]["code"] == "week_needs_practice"


async def test_delete_task(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    body = {"delete_task_ids": [task_id(program, "Lire l'article B")]}
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json=body)
    assert r.status_code == 200
    assert week_load(r.json(), 2) == WEEK2_LOAD - 40


async def test_date_outside_program_is_refused(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    r = await _move(client, task_id(program, "Lire l'article A"), "2027-06-01")
    assert r.status_code == 422 and r.json()["error"]["code"] == "date_outside_program"


async def test_sunday_is_allowed(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    r = await _move(client, task_id(program, "Lire l'article A"), "2026-11-29")
    assert r.status_code == 200


async def test_status_and_title_change(client: httpx.AsyncClient, draft_program: Draft) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire le chapitre 1")
    r = await client.patch(f"{API}/tasks/{tid}", json={"status": "done", "title": "Lire le tome 1"})
    assert r.status_code == 200
    after = await view(client, draft_program.program_id)
    assert after["progress"]["done_tasks"] == 1 and after["progress"]["done_minutes"] == 120


async def test_minutes_over_budget_is_refused(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    r = await client.patch(
        f"{API}/tasks/{task_id(program, 'Faire le quiz 1')}", json={"minutes": 90}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "week_over_budget"


async def test_start_date_shifts_a_draft(client: httpx.AsyncClient, draft_program: Draft) -> None:
    body = {"start_date": "2026-11-23"}
    r = await client.patch(f"{API}/programs/{draft_program.program_id}", json=body)
    assert r.status_code == 200
    assert r.json()["start_date"] == "2026-11-23"
    assert r.json()["weeks"][1]["start_date"] == "2026-11-30"
    assert min(t["planned_date"] for t in tasks_of(r.json())) == "2026-11-23"
    tuesday = await client.patch(
        f"{API}/programs/{draft_program.program_id}", json={"start_date": "2026-11-24"}
    )
    assert tuesday.status_code == 422 and tuesday.json()["error"]["code"] == "invalid_start_date"


async def test_logs_hold_ids_only(
    client: httpx.AsyncClient, draft_program: Draft, caplog: pytest.LogCaptureFixture
) -> None:
    program = await view(client, draft_program.program_id)
    with caplog.at_level(logging.INFO, logger="app"):
        await _move(client, task_id(program, "Lire l'article A"), TUESDAY_W1)
        await client.post(f"{API}/programs/{draft_program.program_id}/validate")
    text = caplog.text
    assert draft_program.program_id in text
    assert "Lire l'article" not in text and "Parcours données" not in text and "pandas" not in text


async def test_concurrent_move_and_add_never_exceed_85_percent(
    client: httpx.AsyncClient, draft_program: Draft, slow_reads: None
) -> None:
    program = await view(client, draft_program.program_id)
    new = {
        "module_id": program["weeks"][0]["modules"][0]["id"],
        "title": "Relire le chapitre 2",
        "type": "lire",
        "minutes": 40,
        "done_criterion": "Notes relues",
        "planned_date": "2026-11-19",
    }
    url = f"{API}/programs/{draft_program.program_id}"
    moved, added = await asyncio.gather(
        _move(client, task_id(program, "Lire l'article A"), TUESDAY_W1),
        client.patch(url, json={"add_tasks": [new]}),
    )
    assert sorted([moved.status_code, added.status_code]) == [200, 422]
    assert week_load(await view(client, draft_program.program_id), 1) == WEEK1_LOAD + 40
