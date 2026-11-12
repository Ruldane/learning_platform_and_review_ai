"""États du tableau : liste dans l'ordre, retouche de January enregistrée comme un nouvel état et
renvoyée au Conseil ouvert comme un message, plafond de 2 Mio sur le corps."""

import httpx
from fastapi import FastAPI

from tests.agents.runtime.runner_helpers import all_events
from tests.features.learning.conftest import GOALS, Stub, Waiting, me, wait_choice
from tests.sessions_support import wait_status

SCENE = {"type": "excalidraw", "elements": [{"id": "a", "type": "text", "text": "Docker"}]}


async def _user_messages(app: FastAPI, sid: str) -> list[str]:
    events = await all_events(app.state.session_factory, me(app), sid)
    return [e.payload.text for e in events if e.type == "user.message"]  # type: ignore[union-attr]


async def test_boards_listed_in_order(client: httpx.AsyncClient, stub: Stub) -> None:
    stub.batches = 2
    waiting = await wait_choice(client)
    boards = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()
    assert [(b["step"], b["kind"], b["author"]) for b in boards] == [
        (1, "comparison", "scribe"),
        (2, "comparison", "scribe"),
    ]
    first = boards[0]
    assert first["session_id"] == waiting.sid and first["scene"] is None
    assert first["mermaid"].startswith("flowchart LR") and first["parent_id"] is None


async def test_board_edit_saves_state_and_messages_the_session(
    client: httpx.AsyncClient, app: FastAPI, council_waiting_choice: Waiting
) -> None:
    waiting = council_waiting_choice
    board = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()[0]
    edit = {"scene": SCENE, "note": "  J'ai ajouté Docker  "}
    r = await client.post(f"/api/v1/boards/{board['id']}/edits", json=edit)
    assert r.status_code == 201
    saved = r.json()
    assert (saved["author"], saved["parent_id"], saved["scene"]) == ("user", board["id"], SCENE)
    assert (saved["step"], saved["kind"], saved["mermaid"]) == (
        board["step"],
        board["kind"],
        board["mermaid"],
    )
    assert (await _user_messages(app, waiting.sid))[-1] == "[Tableau] J'ai ajouté Docker"
    boards = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()
    assert [b["id"] for b in boards] == [board["id"], saved["id"]]


async def test_board_edit_after_council_keeps_state_without_message(
    client: httpx.AsyncClient, app: FastAPI, council_waiting_choice: Waiting
) -> None:
    waiting = council_waiting_choice
    board = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()[0]
    assert (await client.post(f"/api/v1/proposals/{waiting.ids[0]}/choose", json={})).is_success
    await wait_status(client, waiting.sid, "completed")
    edit = {"scene": SCENE, "note": "Après coup"}
    r = await client.post(f"/api/v1/boards/{board['id']}/edits", json=edit)
    assert r.status_code == 201
    assert await _user_messages(app, waiting.sid) == []
    assert len((await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()) == 2


async def test_board_edit_rejects_empty_note_without_echo(
    client: httpx.AsyncClient, council_waiting_choice: Waiting
) -> None:
    board = (await client.get(f"{GOALS}/{council_waiting_choice.goal_id}/boards")).json()[0]
    marker = "contenu-de-scene-7Y"
    r = await client.post(
        f"/api/v1/boards/{board['id']}/edits", json={"scene": {"x": marker}, "note": "   "}
    )
    assert r.status_code == 422 and marker not in r.text
    assert (await client.post("/api/v1/boards/inconnu/edits", json=SCENE)).status_code == 422


async def test_board_edit_over_2_mib_is_413(client: httpx.AsyncClient) -> None:
    image = "data:image/png;base64," + "A" * (2 * 1024 * 1024)
    body = {"scene": {"elements": [], "files": {"img": {"dataURL": image}}}, "note": "Image"}
    r = await client.post("/api/v1/boards/quelconque/edits", json=body)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "board_too_large"
    assert r.json()["error"]["message"] == "Tableau trop volumineux : 2 Mio au maximum."


async def test_board_edit_under_limit_is_accepted(
    client: httpx.AsyncClient, council_waiting_choice: Waiting
) -> None:
    board = (await client.get(f"{GOALS}/{council_waiting_choice.goal_id}/boards")).json()[0]
    image = "data:image/png;base64," + "A" * (1024 * 1024)
    body = {"scene": {"elements": [], "files": {"img": {"dataURL": image}}}, "note": "Image"}
    r = await client.post(f"/api/v1/boards/{board['id']}/edits", json=body)
    assert r.status_code == 201
