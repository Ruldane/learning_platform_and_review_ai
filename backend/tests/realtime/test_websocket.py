"""WebSocket `/sessions/{id}/stream` : rejeu après `after_seq`, direct, fin de session, origine,
isolation, déconnexion du client (aucun abonné laissé derrière)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.db.base import new_id
from app.main import create_app
from tests.sessions_support import API, act_as, wait_status_sync, wait_until_sync


def start(client: TestClient, graph: str) -> str:
    r = client.post(API, json={"graph": graph})
    assert r.status_code == 202, r.text
    return str(r.json()["session_id"])


def stream_url(sid: str, after_seq: int = 0) -> str:
    return f"{API}/{sid}/stream?after_seq={after_seq}"


def test_ws_replays_after_seq(sync_client: TestClient):
    sid = start(sync_client, "one_llm_call")
    n = wait_status_sync(sync_client, sid, "completed")["last_seq"]
    assert n >= 4
    with sync_client.websocket_connect(stream_url(sid, 2)) as ws:
        events = [ws.receive_json() for _ in range(n - 2)]
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()  # session terminée : le serveur ferme après le rejeu
    assert [e["seq"] for e in events] == list(range(3, n + 1))
    assert events[-1]["type"] == "run.completed"
    assert {"id", "session_id", "seq", "ts", "type", "agent", "payload"} <= set(events[0])
    assert closed.value.code == 1000


def test_ws_streams_live_events_then_closes_when_session_ends(sync_client: TestClient):
    sid = start(sync_client, "ask")
    view = wait_status_sync(sync_client, sid, "waiting_user")
    iid = view["pending_interrupt"]["interrupt_id"]
    with sync_client.websocket_connect(stream_url(sid, view["last_seq"])) as ws:
        r = sync_client.post(f"{API}/{sid}/message", json={"text": "Je suis là"})
        assert ws.receive_json()["seq"] == r.json()["seq"]
        sync_client.post(f"{API}/{sid}/resume", json={"interrupt_id": iid, "value": "oui"})
        last = ws.receive_json()
        assert last["type"] == "run.completed"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 1000


def test_ws_closes_after_replay_for_a_cancelled_session(sync_client: TestClient):
    """Annulée : aucun événement de fin, et le bus ne ferme pas un abonné arrivé après coup
    (D42) ; le WebSocket lit le statut et se ferme lui-même."""
    sid = start(sync_client, "ask")
    n = wait_status_sync(sync_client, sid, "waiting_user")["last_seq"]
    assert sync_client.post(f"{API}/{sid}/cancel").json()["status"] == "cancelled"
    with sync_client.websocket_connect(stream_url(sid)) as ws:
        seqs = [ws.receive_json()["seq"] for _ in range(n)]
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert seqs == list(range(1, n + 1))
    assert closed.value.code == 1000


def test_ws_closes_4404_for_foreign_session(sync_client: TestClient, app: FastAPI):
    sid = start(sync_client, "two_steps")
    act_as(app, new_id())
    for target in (sid, new_id()):
        with (
            pytest.raises(WebSocketDisconnect) as closed,
            sync_client.websocket_connect(stream_url(target)) as ws,
        ):
            ws.receive_json()
        assert closed.value.code == 4404


def test_ws_rejects_foreign_origin(sync_client: TestClient):
    sid = start(sync_client, "two_steps")
    headers = {"origin": "https://evil.example"}
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        sync_client.websocket_connect(stream_url(sid), headers=headers) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 1008


def test_ws_accepts_allowed_origins(sync_client: TestClient):
    sid = start(sync_client, "two_steps")
    n = wait_status_sync(sync_client, sid, "completed")["last_seq"]
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        with sync_client.websocket_connect(stream_url(sid), headers={"origin": origin}) as ws:
            assert [ws.receive_json()["seq"] for _ in range(n)] == list(range(1, n + 1))


def test_ws_rejects_negative_after_seq(sync_client: TestClient):
    sid = start(sync_client, "two_steps")
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        sync_client.websocket_connect(stream_url(sid, -1)) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 1008


def test_client_disconnect_releases_the_subscription(sync_client: TestClient, app: FastAPI):
    sid = start(sync_client, "ask")
    n = wait_status_sync(sync_client, sid, "waiting_user")["last_seq"]
    bus = app.state.runtime.bus
    user_id = app.state.local_user_id
    with sync_client.websocket_connect(stream_url(sid)) as ws:
        assert [ws.receive_json()["seq"] for _ in range(n)] == list(range(1, n + 1))
        ws.send_text("ignoré : le flux ne va que du serveur vers le client")
        wait_until_sync(lambda: bus.subscriber_count(user_id=user_id, session_id=sid) == 1)
    wait_until_sync(lambda: bus.subscriber_count(user_id=user_id, session_id=sid) == 0)
    # La session continue sans abonné, et un nouveau client reprend où il veut.
    r = sync_client.post(f"{API}/{sid}/message", json={"text": "toujours là"})
    with sync_client.websocket_connect(stream_url(sid, n)) as ws:
        assert ws.receive_json()["seq"] == r.json()["seq"]


def test_ws_requires_a_user(settings: Settings, app: FastAPI):
    # `app` : schéma de la base créé (le lifespan relit les sessions à reprendre).
    """Mode `google` (phase 9) : la poignée de main est refusée en 401, enveloppe d'erreur."""
    google = create_app(settings.model_copy(update={"auth_mode": "google"}))
    with (
        TestClient(google) as client,
        pytest.raises(WebSocketDenialResponse) as denied,
        client.websocket_connect(stream_url(new_id())),
    ):
        pass
    assert denied.value.status_code == 401
    assert denied.value.json()["error"]["code"] == "auth_required"
