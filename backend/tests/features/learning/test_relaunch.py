"""Relances après échec (revue finale de la phase 4, I1, D97) : « Choisir » de nouveau relance
le Stratège quand sa session a échoué sans programme ; `POST /goals/{id}/council` relance un
Conseil en échec depuis le début, en gardant l'objectif. Mêmes verrous que le lancement
d'origine : jamais deux sessions ouvertes."""

import asyncio

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.learning import Goal
from tests.features.learning.conftest import (
    GOALS,
    Stub,
    chosen_ids,
    count_sessions,
    next_monday,
    proposal_ids,
    start_goal,
    wait_choice,
)
from tests.sessions_support import act_as, wait_status

CHOOSE = "/api/v1/proposals/{}/choose"


async def _program_sid(client: httpx.AsyncClient, goal_id: str) -> str:
    sid: str = (await client.get(f"{GOALS}/{goal_id}")).json()["program_session_id"]
    return sid


async def test_choose_again_relaunches_a_failed_program_builder(
    client: httpx.AsyncClient, stub: Stub
) -> None:
    stub.program_failures = 1
    waiting = await wait_choice(client)
    p1, start = waiting.ids[0], next_monday(2)
    r = await client.post(CHOOSE.format(p1), json={"start_date": start})
    assert r.status_code == 202 and r.json()["already_chosen"] is False
    await wait_status(client, waiting.sid, "completed")
    failed = await _program_sid(client, waiting.goal_id)
    await wait_status(client, failed, "failed")
    replies = await asyncio.gather(*(client.post(CHOOSE.format(p1), json={}) for _ in range(3)))
    assert [r.status_code for r in replies] == [202, 202, 202]
    assert sorted(r.json()["already_chosen"] for r in replies) == [False, True, True]
    retried = await _program_sid(client, waiting.goal_id)
    assert retried != failed
    await wait_status(client, retried, "waiting_user")
    assert await count_sessions(client, "program_builder") == 2
    # Sans date dans la relance : celle de l'entrée précédente, encore à venir.
    assert [x["start_date"] for x in stub.program_inputs] == [start, start]
    assert [x["proposal_ids"] for x in stub.program_inputs] == [[p1], [p1]]
    again = await client.post(CHOOSE.format(p1), json={})
    assert again.json()["already_chosen"] is True  # session ouverte : rien de relancé
    assert await count_sessions(client, "program_builder") == 2
    goal = (await client.get(f"{GOALS}/{waiting.goal_id}")).json()
    assert goal["status"] == "chosen" and await chosen_ids(client, waiting.goal_id) == {p1}


async def test_choose_another_path_after_failed_program_is_409(
    client: httpx.AsyncClient, stub: Stub
) -> None:
    stub.program_failures = 1
    waiting = await wait_choice(client)
    assert (await client.post(CHOOSE.format(waiting.ids[0]), json={})).status_code == 202
    await wait_status(client, waiting.sid, "completed")
    await wait_status(client, await _program_sid(client, waiting.goal_id), "failed")
    r = await client.post(CHOOSE.format(waiting.ids[1]), json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "council_not_waiting"
    assert await count_sessions(client, "program_builder") == 1


async def test_failed_council_is_relaunched_from_scratch(
    client: httpx.AsyncClient, stub: Stub
) -> None:
    stub.council_failures = 1
    goal_id, first = await start_goal(client)
    await wait_status(client, first, "failed")
    old = await proposal_ids(client, goal_id)
    assert old == stub.batch_ids[1]  # lot du Conseil en échec, encore celui de l'objectif
    r = await client.post(f"{GOALS}/{goal_id}/council")
    assert r.status_code == 202
    started = r.json()
    second = started["session_id"]
    assert second != first and started["goal"]["id"] == goal_id
    assert started["goal"]["council_session_id"] == second
    assert started["goal"]["status"] == "council"
    view = await wait_status(client, second, "waiting_user")
    assert view["pending_interrupt"]["kind"] == "choose_path"
    new = await proposal_ids(client, goal_id)
    assert new == stub.batch_ids[1] and not set(new) & set(old)  # l'ancien lot est caché
    assert await count_sessions(client, "learning_council") == 2
    r = await client.post(CHOOSE.format(old[0]), json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "proposal_outdated"
    assert (await client.post(CHOOSE.format(stub.batch_ids[1][0]), json={})).status_code == 202
    await wait_status(client, second, "completed")
    assert await count_sessions(client, "program_builder") == 1


async def test_council_relaunch_refused_unless_last_council_failed(
    client: httpx.AsyncClient, app: FastAPI, stub: Stub
) -> None:
    waiting = await wait_choice(client)
    r = await client.post(f"{GOALS}/{waiting.goal_id}/council")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "council_not_failed"
    assert r.json()["error"]["details"] == {"status": "waiting_user"}
    assert (await client.post(f"{GOALS}/inconnu/council")).status_code == 404
    act_as(app, "autre-utilisateur")
    r = await client.post(f"{GOALS}/{waiting.goal_id}/council")
    assert r.status_code == 404 and r.json()["error"]["code"] == "goal_not_found"
    assert await count_sessions(client, "learning_council") == 0


async def test_council_relaunch_refused_once_a_program_was_launched(
    client: httpx.AsyncClient, app: FastAPI, stub: Stub
) -> None:
    stub.council_failures = 1
    goal_id, first = await start_goal(client)
    await wait_status(client, first, "failed")
    async with app.state.session_factory() as db:
        await db.execute(update(Goal).where(Goal.id == goal_id).values(status="chosen"))
        await db.commit()
    r = await client.post(f"{GOALS}/{goal_id}/council")
    assert r.status_code == 409 and r.json()["error"]["code"] == "goal_already_chosen"
    assert await count_sessions(client, "learning_council") == 1


async def test_concurrent_council_relaunches_start_one_session(
    client: httpx.AsyncClient, stub: Stub
) -> None:
    stub.council_failures = 1
    goal_id, first = await start_goal(client)
    await wait_status(client, first, "failed")
    stub.hold = asyncio.Event()  # le Conseil relancé reste `running`
    replies = await asyncio.gather(*(client.post(f"{GOALS}/{goal_id}/council") for _ in range(3)))
    assert sorted(r.status_code for r in replies) == [202, 409, 409]
    refused = [r.json()["error"] for r in replies if r.status_code == 409]
    assert {(e["code"], e["details"]["status"]) for e in refused} == {
        ("council_not_failed", "running")
    }
    assert await count_sessions(client, "learning_council") == 2
