"""Reprise, pause et annulation par l'API : 409 lisibles (D46), double clic sans double reprise."""

import asyncio

import httpx

from tests.agents.graphs_for_tests import Probe
from tests.sessions_support import API, wait_status


async def waiting(client: httpx.AsyncClient) -> tuple[str, str]:
    """Session `ask` en attente de réponse ; rend `(session_id, interrupt_id)`."""
    r = await client.post(API, json={"graph": "ask"})
    sid = str(r.json()["session_id"])
    view = await wait_status(client, sid, "waiting_user")
    pending = view["pending_interrupt"]
    assert pending["kind"] == "choice" and pending["question"] == "On continue ?"
    assert pending["options"] == [{"value": "oui", "label": "Oui"}]
    return sid, str(pending["interrupt_id"])


def error(r: httpx.Response) -> tuple[int, str]:
    return r.status_code, r.json()["error"]["code"]


async def test_resume_with_stale_interrupt_returns_409(client: httpx.AsyncClient, probe: Probe):
    sid, iid = await waiting(client)
    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": "autre", "value": "oui"})
    assert error(r) == (409, "stale_interrupt")
    assert r.json()["error"]["message"] == "Cette question a déjà reçu une réponse."
    assert r.json()["error"]["details"] == {"status": "waiting_user"}

    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": iid, "value": "oui"})
    assert r.status_code == 202
    assert r.json()["id"] == sid and r.json()["pending_interrupt"] is None
    assert r.json()["status"] in {"running", "completed"}
    view = await wait_status(client, sid, "completed")
    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": iid, "value": "oui"})
    assert error(r) == (409, "stale_interrupt")
    assert probe.counter["after"] == 1
    assert view["last_seq"] > 0


async def test_double_click_resumes_the_graph_once(client: httpx.AsyncClient, probe: Probe):
    sid, iid = await waiting(client)
    body = {"interrupt_id": iid, "value": "oui"}
    first, second = await asyncio.gather(
        client.post(f"{API}/{sid}/resume", json=body),
        client.post(f"{API}/{sid}/resume", json=body),
    )
    assert sorted([first.status_code, second.status_code]) == [202, 409]
    await wait_status(client, sid, "completed")
    assert probe.counter["after"] == 1


async def test_resume_without_interrupt_id_while_waiting_returns_409(client: httpx.AsyncClient):
    sid, _ = await waiting(client)
    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": None, "value": None})
    assert error(r) == (409, "interrupt_required")


async def test_resume_finished_session_returns_409(client: httpx.AsyncClient):
    sid = str((await client.post(API, json={"graph": "two_steps"})).json()["session_id"])
    await wait_status(client, sid, "completed")
    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": None, "value": None})
    assert error(r) == (409, "session_not_resumable")
    assert r.json()["error"]["details"] == {"status": "completed"}


async def test_pause_then_resume_asks_the_same_question(client: httpx.AsyncClient):
    sid, iid = await waiting(client)
    r = await client.post(f"{API}/{sid}/pause")
    assert r.status_code == 200
    assert r.json()["status"] == "paused" and r.json()["pending_interrupt"] is None
    again = await client.post(f"{API}/{sid}/pause")  # idempotent
    assert again.status_code == 200 and again.json()["status"] == "paused"

    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": None, "value": None})
    assert r.status_code == 202
    view = await wait_status(client, sid, "waiting_user")
    assert view["pending_interrupt"]["interrupt_id"] == iid


async def test_resume_accepts_an_empty_body_for_a_pause(client: httpx.AsyncClient):
    sid, _ = await waiting(client)
    await client.post(f"{API}/{sid}/pause")
    r = await client.post(f"{API}/{sid}/resume", json={})
    assert r.status_code == 202
    await wait_status(client, sid, "waiting_user")


async def test_cancel_then_every_action_is_refused(client: httpx.AsyncClient):
    sid, iid = await waiting(client)
    r = await client.post(f"{API}/{sid}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert error(await client.post(f"{API}/{sid}/cancel")) == (409, "session_not_cancellable")
    assert error(await client.post(f"{API}/{sid}/pause")) == (409, "session_not_pausable")
    r = await client.post(f"{API}/{sid}/resume", json={"interrupt_id": iid, "value": "oui"})
    assert error(r) == (409, "stale_interrupt")
    r = await client.post(f"{API}/{sid}/message", json={"text": "allô"})
    assert error(r) == (409, "session_closed")


async def test_cancel_a_running_session(client: httpx.AsyncClient, probe: Probe):
    sid = str((await client.post(API, json={"graph": "blocking"})).json()["session_id"])
    await asyncio.wait_for(probe.b_started.wait(), 5)
    r = await client.post(f"{API}/{sid}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert probe.counter["B"] == 1
