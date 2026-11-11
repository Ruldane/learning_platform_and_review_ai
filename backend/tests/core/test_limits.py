"""Limite de taille du corps des requêtes (`BodySizeLimit`), avant toute analyse du multipart."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import FastAPI, Request

from app.core.errors import register_error_handlers
from app.core.limits import BodySizeLimit

MAX = 10
ENVELOPE = {
    "error": {
        "code": "file_too_large",
        "message": "Fichier trop volumineux : 20 Mo au maximum.",
        "details": None,
    }
}


def _app(calls: list[int]) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.add_middleware(BodySizeLimit, path="/api/v1/documents", max_bytes=MAX)

    @app.post("/api/v1/documents")
    async def upload(request: Request) -> dict[str, int]:
        size = len(await request.body())
        calls.append(size)
        return {"size": size}

    @app.post("/api/v1/other")
    async def other(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_content_length_over_limit_rejected_before_reading() -> None:
    calls: list[int] = []
    received: list[Any] = []
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        received.append(1)
        return {"type": "http.request", "body": b"x" * 100, "more_body": False}

    async def send(message: Any) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/documents",
        "headers": [(b"content-length", b"100")],
    }
    await BodySizeLimit(_app(calls), path="/api/v1/documents", max_bytes=MAX)(scope, receive, send)
    assert received == [] and calls == []
    assert sent[0]["status"] == 413
    assert b'"file_too_large"' in sent[1]["body"]


async def test_body_over_limit_without_content_length_is_413() -> None:
    calls: list[int] = []

    async def stream() -> AsyncIterator[bytes]:
        for _ in range(5):
            yield b"abcd"

    async with _client(_app(calls)) as client:
        r = await client.post("/api/v1/documents", content=stream())
    assert r.status_code == 413 and r.json() == ENVELOPE
    assert calls == []


async def test_body_at_the_limit_is_accepted() -> None:
    calls: list[int] = []

    async def stream() -> AsyncIterator[bytes]:
        yield b"abcde"
        yield b"fghij"

    async with _client(_app(calls)) as client:
        r = await client.post("/api/v1/documents", content=stream())
        declared = await client.post("/api/v1/documents", content=b"x" * MAX)
    assert r.status_code == 200 and r.json() == {"size": MAX}
    assert declared.status_code == 200 and calls == [MAX, MAX]


async def test_other_paths_unaffected() -> None:
    async with _client(_app([])) as client:
        r = await client.post("/api/v1/other", content=b"x" * 100)
        listing = await client.get("/api/v1/documents")
    assert r.status_code == 200 and r.json() == {"size": 100}
    assert listing.status_code == 405  # route POST seulement : la garde n'y touche pas


async def test_invalid_content_length_is_left_to_the_server() -> None:
    """Un `Content-Length` illisible n'est pas une raison de refuser : le décompte s'applique."""
    calls: list[int] = []
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"x" * 100, "more_body": False}

    async def send(message: Any) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/documents",
        "headers": [(b"content-length", b"abc")],
        "query_string": b"",
    }
    await BodySizeLimit(_app(calls), path="/api/v1/documents", max_bytes=MAX)(scope, receive, send)
    assert calls == [] and sent[0]["status"] == 413
