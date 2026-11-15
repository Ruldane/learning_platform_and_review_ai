"""`POST /applications/intake` (D141) : 202 et la session de l'Assistant de suivi, 409 tant qu'une
autre attend, 422 sans écho de la phrase, accès sans connexion."""

import httpx
from fastapi import FastAPI

from tests.features.applications.conftest import API
from tests.features.lessons.conftest import RecordingLauncher

ROOT = "/api/v1"
SENTENCE = "j'ai postulé hier chez Société Fictive pour le poste Développeuse IA"


def spy(app: FastAPI) -> RecordingLauncher:
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.career.applications.launcher = launcher
    return launcher


async def test_intake_route_202_and_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    r = await client.post(f"{API}/intake", json={"text": f"  {SENTENCE}  "})
    assert r.status_code == 202, r.text
    first = r.json()["session_id"]
    assert r.json() == {"session_id": first}
    assert launcher.started == [("application_intake", {"text": SENTENCE})]  # blancs retirés
    again = await client.post(f"{API}/intake", json={"text": "autre phrase"})
    assert (again.status_code, again.json()["error"]["code"]) == (409, "intake_in_progress")
    assert again.json()["error"]["details"] == {"session_id": first}
    assert "autre phrase" not in again.text
    assert len(launcher.started) == 1


async def test_intake_runs_again_once_the_session_is_over(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    first = (await client.post(f"{API}/intake", json={"text": SENTENCE})).json()["session_id"]
    assert (await client.post(f"{ROOT}/sessions/{first}/cancel")).status_code == 200
    second = await client.post(f"{API}/intake", json={"text": SENTENCE})
    assert second.status_code == 202 and second.json()["session_id"] != first
    assert len(launcher.started) == 2


async def test_intake_session_has_its_subject(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    sid = (await client.post(f"{API}/intake", json={"text": SENTENCE})).json()["session_id"]
    view = (await client.get(f"{ROOT}/sessions/{sid}")).json()
    assert (view["graph"], view["subject_type"]) == ("application_intake", "application_intake")


async def test_intake_422_never_echoes_the_sentence(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    for body in ({"text": ""}, {"text": "   "}, {"text": "x" * 1001}, {}, {"text": 3}):
        r = await client.post(f"{API}/intake", json=body)
        assert r.status_code == 422, body
        assert r.json()["error"]["details"] == {"fields": ["text"]}
    assert "x" * 50 not in (await client.post(f"{API}/intake", json={"text": "x" * 1001})).text
    assert launcher.started == []


async def test_intake_graph_is_not_started_by_the_generic_route(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{ROOT}/sessions", json={"graph": "application_intake", "input": {"text": SENTENCE}}
    )
    assert (r.status_code, r.json()["error"]["code"]) == (409, "graph_has_route")
    assert r.json()["error"]["details"]["route"] == "POST /applications/intake"


async def test_intake_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    r = await client_google_mode.post(f"{API}/intake", json={"text": SENTENCE})
    assert r.status_code == 401
