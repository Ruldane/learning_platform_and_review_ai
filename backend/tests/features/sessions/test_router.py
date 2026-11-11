"""API REST des sessions (SPEC 14.1) : démarrage, lecture, liste, messages, erreurs, isolation."""

import time
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import SessionRepository
from app.db.base import new_id
from app.features.sessions.service import find_active_session
from tests.agents.graphs_for_tests import Probe
from tests.sessions_support import API, act_as, wait_status


async def start(client: httpx.AsyncClient, graph: str, **body: object) -> str:
    r = await client.post(API, json={"graph": graph, **body})
    assert r.status_code == 202, r.text
    return str(r.json()["session_id"])


async def test_post_sessions_returns_id_fast(client: httpx.AsyncClient, probe: Probe):
    # Le graphe reste bloqué : la réponse n'attend pas son exécution.
    began = time.perf_counter()
    r = await client.post(API, json={"graph": "blocking", "input": {}})
    assert time.perf_counter() - began < 2
    assert r.status_code == 202 and r.json()["session_id"]
    view = await wait_status(client, r.json()["session_id"], "running")
    assert view["graph"] == "blocking"


async def test_unknown_graph_returns_404_in_french(client: httpx.AsyncClient):
    r = await client.post(API, json={"graph": "nope"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_graph"
    assert r.json()["error"]["message"].startswith("Parcours inconnu")


async def test_invalid_input_returns_422_without_echoing_values(client: httpx.AsyncClient):
    r = await client.post(API, json={"graph": "with_topic", "input": {"topic": {"k": "sk-secret"}}})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_input"
    assert r.json()["error"]["details"] == {"fields": ["topic"]}
    assert "sk-secret" not in r.text


async def test_request_validation_never_echoes_input(client: httpx.AsyncClient):
    sid = await start(client, "ask")
    await wait_status(client, sid, "waiting_user")
    r = await client.post(f"{API}/{sid}/message", json={"text": "sk-" + "x" * 5000})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert "sk-xxx" not in r.text
    r = await client.post(API, json={"input": {"secret": "sk-other"}})
    assert r.status_code == 422 and "sk-other" not in r.text


async def test_get_returns_session_view(client: httpx.AsyncClient):
    sid = await start(client, "one_llm_call")
    view = await wait_status(client, sid, "completed")
    assert view["id"] == sid and view["graph"] == "one_llm_call"
    assert view["pending_interrupt"] is None and view["error"] is None
    assert view["tokens_in"] > 0 and view["tokens_out"] > 0 and view["cost_usd"] >= 0
    assert view["last_seq"] >= 4  # agent.started, tokens..., agent.message, cost, run.completed
    assert view["created_at"] and view["updated_at"]


async def test_session_view_exposes_subject(client: httpx.AsyncClient, probe: Probe):
    doc_id = new_id()
    sid = await start(client, "blocking", subject_type="document", subject_id=doc_id)
    body = (await client.get(f"{API}/{sid}")).json()
    assert body["subject_type"] == "document" and body["subject_id"] == doc_id
    listed = (await client.get(API)).json()
    assert (listed[0]["subject_type"], listed[0]["subject_id"]) == ("document", doc_id)
    plain = await start(client, "two_steps")
    view = await wait_status(client, plain, "completed")
    assert view["subject_type"] is None and view["subject_id"] is None


async def test_find_active_session_picks_latest_open_session_of_the_subject(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [  # (utilisateur, graphe, statut, objet, minutes)
        ("u1", "learned_document", "completed", "d1", 9),
        ("u1", "learned_document", "paused", "d1", 1),
        ("u1", "learned_document", "waiting_user", "d1", 2),
        ("u1", "learned_document", "running", "d2", 8),
        ("u1", "other_graph", "running", "d1", 7),
        ("u2", "learned_document", "running", "d1", 6),
    ]
    ids: list[str] = []
    async with db_session_factory() as db:
        for user, graph, status, subject, minutes in rows:
            row = await SessionRepository(db, user).add(
                graph=graph,
                status=status,
                subject_type="document",
                subject_id=subject,
                created_at=t0 + timedelta(minutes=minutes),
            )
            ids.append(row.id)
        await db.commit()

        async def find(user: str, subject: str) -> str | None:
            return await find_active_session(
                db, user, graph="learned_document", subject_type="document", subject_id=subject
            )

        assert await find("u1", "d1") == ids[2]  # la plus récente encore ouverte
        assert await find("u1", "d2") == ids[3]
        assert await find("u2", "d1") == ids[5]
        assert await find("u1", "d3") is None and await find("u3", "d1") is None


async def test_get_unknown_session_returns_404(client: httpx.AsyncClient):
    r = await client.get(f"{API}/{new_id()}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "session_not_found"
    assert r.json()["error"]["message"] == "Session introuvable."


async def test_failed_session_exposes_its_error(client: httpx.AsyncClient):
    sid = await start(client, "crash")
    view = await wait_status(client, sid, "failed")
    assert view["error"]["code"] == "internal_error" and view["error"]["message"]


async def test_message_creates_user_message_event(client: httpx.AsyncClient):
    sid = await start(client, "ask")
    before = await wait_status(client, sid, "waiting_user")
    r = await client.post(f"{API}/{sid}/message", json={"text": "Plutôt demain"})
    assert r.status_code == 201
    event = r.json()
    assert event["type"] == "user.message" and event["payload"] == {"text": "Plutôt demain"}
    assert event["session_id"] == sid and event["seq"] == before["last_seq"] + 1
    assert (await client.get(f"{API}/{sid}")).json()["last_seq"] == event["seq"]


async def test_message_to_finished_session_returns_409(client: httpx.AsyncClient):
    sid = await start(client, "two_steps")
    await wait_status(client, sid, "completed")
    r = await client.post(f"{API}/{sid}/message", json={"text": "Encore ?"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "session_closed"
    assert r.json()["error"]["details"] == {"status": "completed"}


async def test_message_rejects_empty_text(client: httpx.AsyncClient):
    sid = await start(client, "ask")
    r = await client.post(f"{API}/{sid}/message", json={"text": ""})
    assert r.status_code == 422


async def test_list_filters_by_graph_and_status(client: httpx.AsyncClient, probe: Probe):
    done = await start(client, "two_steps")
    asking = await start(client, "ask")
    running = await start(client, "blocking")
    await wait_status(client, done, "completed")
    await wait_status(client, asking, "waiting_user")

    async def ids(query: str) -> set[str]:
        r = await client.get(f"{API}{query}")
        assert r.status_code == 200
        return {view["id"] for view in r.json()}

    assert await ids("") == {done, asking, running}
    assert await ids("?graph=ask") == {asking}
    assert await ids("?status=completed") == {done}
    assert await ids("?graph=blocking&status=running") == {running}
    assert await ids("?graph=two_steps&status=running") == set()
    listed = (await client.get(API)).json()
    assert [v["id"] for v in listed] == [running, asking, done]  # plus récentes d'abord
    assert next(v for v in listed if v["id"] == done)["last_seq"] > 0


async def test_list_rejects_unknown_status(client: httpx.AsyncClient):
    r = await client.get(f"{API}?status=sleeping")
    assert r.status_code == 422 and "sleeping" not in r.text


async def test_other_user_cannot_read_or_drive_session(client: httpx.AsyncClient, app: FastAPI):
    sid = await start(client, "ask")
    await wait_status(client, sid, "waiting_user")
    act_as(app, new_id())
    calls = [
        ("get", f"{API}/{sid}", None),
        ("post", f"{API}/{sid}/resume", {"interrupt_id": "x", "value": "oui"}),
        ("post", f"{API}/{sid}/message", {"text": "x"}),
        ("post", f"{API}/{sid}/pause", None),
        ("post", f"{API}/{sid}/cancel", None),
    ]
    for method, path, body in calls:
        r = await client.request(method, path, json=body)
        assert r.status_code == 404, (path, r.text)
        assert r.json()["error"]["code"] == "session_not_found"
    assert (await client.get(API)).json() == []
    app.dependency_overrides.clear()
    assert (await client.get(f"{API}/{sid}")).json()["status"] == "waiting_user"


async def test_server_stopping_returns_503(client: httpx.AsyncClient, app: FastAPI):
    await app.state.runtime.runner.shutdown()
    r = await client.post(API, json={"graph": "two_steps"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "server_stopping"


async def test_openapi_exposes_session_types(client: httpx.AsyncClient):
    schema = (await client.get("/api/openapi.json")).json()
    view = schema["components"]["schemas"]["SessionView"]
    assert set(view["properties"]["status"]["enum"]) == {
        "running",
        "waiting_user",
        "paused",
        "completed",
        "failed",
        "cancelled",
    }
    assert "SessionEvent" in schema["components"]["schemas"]
    assert "InterruptRequestedPayload" in schema["components"]["schemas"]
    paths = schema["paths"]
    assert {"/api/v1/sessions", "/api/v1/sessions/{session_id}"} <= set(paths)
    for action in ("resume", "message", "pause", "cancel"):
        assert f"/api/v1/sessions/{{session_id}}/{action}" in paths
