"""WebSocket `/sessions/{id}/stream` en mode Google : sans cookie de session valide, la poignée de
main est refusée en 401 `auth_required` ; avec lui, l'origine du front est exigée (CORS ne couvre
pas les WebSockets) ; la session d'un autre compte reste introuvable."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.base import new_id
from app.main import create_app
from tests.features.auth.support import CAMILLE, DOMINIQUE, FakeGoogle, location_query
from tests.sessions_support import API, wait_status_sync

pytestmark = pytest.mark.timeout(15)

FRONT_ORIGIN = "http://localhost:5173"
LOGIN = "/api/v1/auth/google/login"
CALLBACK = "/api/v1/auth/google/callback"


def sign_in(client: TestClient, google: FakeGoogle, email: str) -> str:
    """Un tour de connexion complet ; rend la valeur du cookie de session (le client la garde)."""
    google.email, google.sub = email, f"sub-{email.split('@')[0]}"
    started = client.get(LOGIN, follow_redirects=False)
    query = location_query(started)
    google.nonce = query["nonce"]
    back = client.get(
        CALLBACK, params={"code": "c", "state": query["state"]}, follow_redirects=False
    )
    assert back.status_code == 302 and back.headers["location"].endswith("/"), back.headers
    token = client.cookies.get("tremplin_session")
    assert token
    return token


@pytest.fixture
def google_client(
    google_settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> Iterator[TestClient]:
    app = create_app(
        google_settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    with TestClient(app) as client:
        client.app.state.fake_google = FakeGoogle(google_settings)  # type: ignore[attr-defined]
        client.app.state.fake_google.plug_into(client.app)  # type: ignore[attr-defined]
        yield client


def google_of(client: TestClient) -> FakeGoogle:
    google: FakeGoogle = client.app.state.fake_google  # type: ignore[attr-defined]
    return google


def stream(sid: str) -> str:
    return f"{API}/{sid}/stream"


def test_websocket_without_cookie_refused(google_client: TestClient) -> None:
    for headers in ({}, {"cookie": "tremplin_session=forged-0000"}):
        with (
            pytest.raises(WebSocketDenialResponse) as denied,
            google_client.websocket_connect(stream(new_id()), headers=headers),
        ):
            pass
        assert denied.value.status_code == 401
        assert denied.value.json()["error"]["code"] == "auth_required"


def test_websocket_with_cookie_streams(google_client: TestClient) -> None:
    token = sign_in(google_client, google_of(google_client), CAMILLE)
    started = google_client.post(API, json={"graph": "one_llm_call"})
    assert started.status_code == 202, started.text
    sid = started.json()["session_id"]
    last = wait_status_sync(google_client, sid, "completed")["last_seq"]
    headers = {"cookie": f"tremplin_session={token}", "origin": FRONT_ORIGIN}
    with google_client.websocket_connect(f"{stream(sid)}?after_seq=0", headers=headers) as ws:
        events = [ws.receive_json() for _ in range(last)]
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert [e["seq"] for e in events] == list(range(1, last + 1))
    assert closed.value.code == 1000


def test_websocket_refuses_a_foreign_origin_even_with_a_valid_cookie(
    google_client: TestClient,
) -> None:
    token = sign_in(google_client, google_of(google_client), CAMILLE)
    sid = google_client.post(API, json={"graph": "one_llm_call"}).json()["session_id"]
    wait_status_sync(google_client, sid, "completed")
    for origin in ("https://evil.example.org", "http://localhost:6666", "null"):
        headers = {"cookie": f"tremplin_session={token}", "origin": origin}
        with (
            pytest.raises(WebSocketDisconnect) as closed,
            google_client.websocket_connect(stream(sid), headers=headers),
        ):
            pass
        assert closed.value.code == 1008, origin


def test_websocket_without_origin_is_refused_in_google_mode(google_client: TestClient) -> None:
    """Un navigateur envoie toujours `Origin` : sans lui (client hors navigateur), même avec un
    cookie valide, la poignée de main est refusée (1008). Sans cookie, le refus reste la 401."""
    token = sign_in(google_client, google_of(google_client), CAMILLE)
    sid = google_client.post(API, json={"graph": "one_llm_call"}).json()["session_id"]
    wait_status_sync(google_client, sid, "completed")
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        google_client.websocket_connect(
            stream(sid), headers={"cookie": f"tremplin_session={token}"}
        ),
    ):
        pass
    assert closed.value.code == 1008
    google_client.cookies.clear()
    with (
        pytest.raises(WebSocketDenialResponse) as denied,
        google_client.websocket_connect(stream(sid)),
    ):
        pass
    assert denied.value.status_code == 401  # l'authentification passe avant l'origine


def test_websocket_of_another_account_session_is_closed_4404(google_client: TestClient) -> None:
    google = google_of(google_client)
    sign_in(google_client, google, CAMILLE)
    sid = google_client.post(API, json={"graph": "one_llm_call"}).json()["session_id"]
    wait_status_sync(google_client, sid, "completed")
    other = sign_in(google_client, google, DOMINIQUE)  # le client garde le cookie du second
    headers = {"cookie": f"tremplin_session={other}", "origin": FRONT_ORIGIN}
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        google_client.websocket_connect(stream(sid), headers=headers) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 4404


def test_websocket_after_logout_is_refused(google_client: TestClient) -> None:
    token = sign_in(google_client, google_of(google_client), CAMILLE)
    sid = google_client.post(API, json={"graph": "one_llm_call"}).json()["session_id"]
    assert google_client.post("/api/v1/auth/logout").status_code == 204
    with (
        pytest.raises(WebSocketDenialResponse) as denied,
        google_client.websocket_connect(
            stream(sid), headers={"cookie": f"tremplin_session={token}", "origin": FRONT_ORIGIN}
        ),
    ):
        pass
    assert denied.value.status_code == 401
