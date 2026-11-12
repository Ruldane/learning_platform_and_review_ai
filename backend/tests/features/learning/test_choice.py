"""Choix du parcours par la route : reprise de l'interruption `choose_path`, mélange, refus, et
idempotence sous le verrou de l'objectif (double clic, reprise générique) : un seul
`program_builder`, une seule proposition choisie par lot (Review Focus n° 2)."""

import asyncio

import httpx

from tests.features.learning.conftest import (
    GOALS,
    Stub,
    Waiting,
    chosen_ids,
    count_sessions,
    start_goal,
    wait_choice,
)
from tests.sessions_support import wait_status

CHOOSE = "/api/v1/proposals/{}/choose"


async def _choose(
    client: httpx.AsyncClient, proposal_id: str, body: dict[str, object] | None = None
) -> httpx.Response:
    return await client.post(CHOOSE.format(proposal_id), json=body or {})


async def test_choose_resumes_council_with_choice(
    client: httpx.AsyncClient, council_waiting_choice: Waiting, stub: Stub
) -> None:
    waiting = council_waiting_choice
    p1 = waiting.ids[0]
    r = await _choose(client, p1)
    assert r.status_code == 202
    assert r.json()["council_session_id"] == waiting.sid
    assert r.json()["status"] in {"running", "completed"}
    await wait_status(client, waiting.sid, "completed")
    assert stub.resumed == [{"action": "choose", "proposal_ids": [p1], "start_date": None}]
    assert await chosen_ids(client, waiting.goal_id) == {p1}
    assert await count_sessions(client, "program_builder") == 1
    assert stub.program_inputs[0]["proposal_ids"] == [p1]
    goal = (await client.get(f"{GOALS}/{waiting.goal_id}")).json()
    assert goal["status"] == "chosen" and goal["program_session_id"] is not None
    assert goal["program_id"] is None  # le Stratège n'a encore rien enregistré


async def test_choose_mix_with_start_date(
    client: httpx.AsyncClient, council_waiting_choice: Waiting, stub: Stub
) -> None:
    waiting = council_waiting_choice
    p1, p3 = waiting.ids[0], waiting.ids[2]
    r = await _choose(client, p3, {"mix_with": p1, "start_date": "2026-12-07"})
    assert r.status_code == 202
    await wait_status(client, waiting.sid, "completed")
    value = {"action": "mix", "proposal_ids": [p3, p1], "start_date": "2026-12-07"}
    assert stub.resumed == [value]
    assert await chosen_ids(client, waiting.goal_id) == {p1, p3}
    program = stub.program_inputs[0]
    assert (program["proposal_ids"], program["start_date"]) == ([p3, p1], "2026-12-07")


async def test_choose_mix_requires_two_of_latest_batch(
    client: httpx.AsyncClient, stub: Stub
) -> None:
    stub.batches = 2
    waiting = await wait_choice(client)
    old, p1 = stub.batch_ids[1][0], waiting.ids[0]
    for mix_with in [old, p1, "inconnue"]:
        r = await _choose(client, p1, {"mix_with": mix_with})
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_mix"
    r = await _choose(client, old)  # proposition d'un lot précédent
    assert r.status_code == 409 and r.json()["error"]["code"] == "proposal_outdated"
    assert (await _choose(client, "inconnue")).status_code == 404
    assert stub.resumed == [] and await chosen_ids(client, waiting.goal_id) == set()
    view = (await client.get(f"/api/v1/sessions/{waiting.sid}")).json()
    assert view["status"] == "waiting_user"


async def test_concurrent_choose_starts_one_program_session(
    client: httpx.AsyncClient, council_waiting_choice: Waiting, stub: Stub
) -> None:
    waiting = council_waiting_choice
    p1 = waiting.ids[0]
    replies = await asyncio.gather(*(_choose(client, p1) for _ in range(3)))
    assert [r.status_code for r in replies] == [202, 202, 202]
    assert {r.json()["council_session_id"] for r in replies} == {waiting.sid}
    assert sorted(r.json()["already_chosen"] for r in replies) == [False, True, True]
    await wait_status(client, waiting.sid, "completed")
    assert await count_sessions(client, "program_builder") == 1
    assert await chosen_ids(client, waiting.goal_id) == {p1}
    assert len(stub.resumed) == 1


async def test_concurrent_different_choices_keep_one(
    client: httpx.AsyncClient, council_waiting_choice: Waiting
) -> None:
    waiting = council_waiting_choice
    p1, p2 = waiting.ids[0], waiting.ids[1]
    both = await asyncio.gather(_choose(client, p1), _choose(client, p2))
    replies = dict(zip((p1, p2), both, strict=True))
    assert sorted(r.status_code for r in replies.values()) == [202, 409]
    winner = next(pid for pid, r in replies.items() if r.status_code == 202)
    loser = replies[p2 if winner == p1 else p1]
    assert loser.json()["error"]["code"] == "council_not_waiting"
    await wait_status(client, waiting.sid, "completed")
    assert await chosen_ids(client, waiting.goal_id) == {winner}
    assert await count_sessions(client, "program_builder") == 1


async def test_choose_after_generic_resume_is_idempotent(
    client: httpx.AsyncClient, council_waiting_choice: Waiting
) -> None:
    waiting = council_waiting_choice
    p1, p2 = waiting.ids[0], waiting.ids[1]
    view = (await client.get(f"/api/v1/sessions/{waiting.sid}")).json()
    answer = {"action": "choose", "proposal_ids": [p1]}
    body = {"interrupt_id": view["pending_interrupt"]["interrupt_id"], "value": answer}
    r = await client.post(f"/api/v1/sessions/{waiting.sid}/resume", json=body)
    assert r.status_code == 202
    await wait_status(client, waiting.sid, "completed")
    r = await _choose(client, p1, {"start_date": "2027-01-04"})
    assert r.status_code == 202 and r.json()["status"] == "completed"
    assert r.json()["already_chosen"] is True  # rien changé, date de début comprise
    r = await _choose(client, p2)  # un autre parcours, Conseil terminé
    assert r.status_code == 409 and r.json()["error"]["code"] == "council_not_waiting"
    assert await count_sessions(client, "program_builder") == 1
    assert await chosen_ids(client, waiting.goal_id) == {p1}


async def test_generic_another_round_then_choose(client: httpx.AsyncClient, stub: Stub) -> None:
    waiting = await wait_choice(client)
    view = (await client.get(f"/api/v1/sessions/{waiting.sid}")).json()
    body = {"interrupt_id": view["pending_interrupt"]["interrupt_id"], "value": "another_round"}
    assert (await client.post(f"/api/v1/sessions/{waiting.sid}/resume", json=body)).is_success
    await wait_status(client, waiting.sid, "waiting_user")
    latest = (await client.get(f"{GOALS}/{waiting.goal_id}/proposals")).json()
    assert [p["batch"] for p in latest] == [2, 2, 2]
    old = await _choose(client, waiting.ids[0])
    assert old.status_code == 409 and old.json()["error"]["code"] == "proposal_outdated"
    assert (await _choose(client, latest[1]["id"])).status_code == 202
    await wait_status(client, waiting.sid, "completed")
    assert await chosen_ids(client, waiting.goal_id) == {latest[1]["id"]}


async def test_choose_when_council_running_is_409(client: httpx.AsyncClient, stub: Stub) -> None:
    stub.hold = asyncio.Event()
    goal_id, sid = await start_goal(client)
    async with asyncio.timeout(5):
        while not stub.batch_ids:
            await asyncio.sleep(0.01)
    p1 = stub.batch_ids[1][0]
    r = await _choose(client, p1)
    assert r.status_code == 409
    assert r.json()["error"] == {
        "code": "council_not_waiting",
        "message": "Le Conseil n'attend pas de choix pour le moment.",
        "details": {"status": "running"},
    }
    assert await chosen_ids(client, goal_id) == set()
    stub.hold.set()
    await wait_status(client, sid, "waiting_user")
    assert (await _choose(client, p1)).status_code == 202
    await wait_status(client, sid, "completed")
    assert await count_sessions(client, "program_builder") == 1
