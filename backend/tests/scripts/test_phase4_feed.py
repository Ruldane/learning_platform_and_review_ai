"""Lecture des événements par WebSocket (`websocket_feed`) contre un petit serveur local : une
erreur réseau, un flux fermé trop tôt ou une session inconnue donnent un `CheckFailed` en
français, jamais une trace Python. Le cas nominal sur l'application réelle est dans
`test_check_phase4`."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

from scripts.phase4_steps import CheckFailed, websocket_feed
from tests.scripts.live_server import serving

LAST_SEQ = 3


def _event(seq: int) -> dict[str, Any]:
    return {"seq": seq, "type": "agent.started", "agent": "scout", "payload": {"step": "plan"}}


def stream_app(sent: int, *, stream: bool = True) -> FastAPI:
    """Session `s1` annoncée à `last_seq` 3 ; son flux envoie `sent` événements puis ferme.
    Sans `stream`, la route WebSocket n'existe pas (la poignée de main échoue)."""
    app = FastAPI()

    @app.get("/api/v1/sessions/{session_id}")
    async def view(session_id: str) -> JSONResponse:
        if session_id != "s1":
            return JSONResponse({"error": {"code": "session_not_found"}}, status_code=404)
        return JSONResponse({"id": session_id, "last_seq": LAST_SEQ})

    async def events(socket: WebSocket, session_id: str) -> None:
        await socket.accept()
        for seq in range(1, sent + 1):
            await socket.send_json(_event(seq))
        await socket.close()

    if stream:
        app.add_api_websocket_route("/api/v1/sessions/{session_id}/stream", events)
    return app


async def read(app: FastAPI, session_id: str = "s1") -> list[dict[str, Any]]:
    """Les événements de `session_id` lus par `websocket_feed` sur `app` servie en local."""
    async with serving(app, lifespan="off") as base, httpx.AsyncClient(base_url=base) as client:
        return await websocket_feed(client)(session_id)


async def test_the_feed_reads_up_to_the_last_seq() -> None:
    found = await read(stream_app(LAST_SEQ))

    assert [event["seq"] for event in found] == [1, 2, 3]


async def test_a_stream_closed_too_early_is_a_check_failure() -> None:
    with pytest.raises(CheckFailed, match="Flux fermé après 1 événement") as caught:
        await read(stream_app(1))

    assert caught.value.step == "conseil"


async def test_a_stream_that_cannot_open_is_a_check_failure() -> None:
    with pytest.raises(CheckFailed, match="Flux d'événements injoignable"):
        await read(stream_app(LAST_SEQ, stream=False))


async def test_an_unknown_session_is_a_check_failure() -> None:
    with pytest.raises(CheckFailed, match=r"HTTP 404 \(session_not_found\)"):
        await read(stream_app(LAST_SEQ), "autre")


async def test_an_unreachable_api_is_a_check_failure() -> None:
    async with serving(stream_app(LAST_SEQ), lifespan="off") as base:
        pass  # le serveur est arrêté : son port ne répond plus
    async with httpx.AsyncClient(base_url=base) as client:
        with pytest.raises(CheckFailed, match="API injoignable"):
            await websocket_feed(client)("s1")
