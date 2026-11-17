"""Correctifs de la relecture de sécurité de 10.B1 : porte locale sur `/api/v1/mcp/*` (I1), plafond
du journal et des écritures (I2), seaux de refus (M1), motifs de clés (M2, M3), entrées limites
(M5, M7)."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from app.bootstrap_mcp import install_gate
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.models.mcp import McpCall, McpToken
from app.features.mcp.service.calls import RETENTION_DAYS, purge_old_calls
from app.mcp.auth import check_local_origin
from app.mcp.endpoint import _read_body
from app.mcp.envelope import envelope, scrub_text
from app.mcp.limits import Limits
from tests.mcp.support import API, FakeDispatcher, FakeTools, Mcp, bearer

TOKEN = "tmcp_" + "B" * 43


def _local(client: httpx.AsyncClient) -> dict[str, str]:
    return {"Host": "localhost"}


async def test_management_routes_need_a_local_host_in_local_mode(client: httpx.AsyncClient) -> None:
    """Le client de test se présente comme `Host: test` : refusé avant toute lecture."""
    for method, path in (
        ("GET", "/mcp/settings"),
        ("PUT", "/mcp/settings"),
        ("POST", "/mcp/tokens"),
        ("GET", "/mcp/confirmations"),
        ("POST", "/mcp/changes/x/undo"),
    ):
        response = await client.request(method, f"{API}{path}", json=None)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["error"]["code"] == "host_not_allowed"
    local = await client.get(f"{API}/mcp/settings", headers=_local(client))
    assert local.status_code == 200
    evil = await client.get(
        f"{API}/mcp/settings", headers={"Host": "localhost", "Origin": "https://evil.example"}
    )
    assert evil.status_code == 403 and evil.json()["error"]["code"] == "origin_not_allowed"
    app_origin = await client.get(
        f"{API}/mcp/settings", headers={"Host": "localhost:8000", "Origin": "http://localhost:5173"}
    )
    assert app_origin.status_code == 200
    # Le reste de l'API n'est pas concerné.
    assert (await client.get(f"{API}/postings")).status_code == 200


async def test_bearer_token_on_management_routes_is_refused_in_local_mode(
    client: httpx.AsyncClient,
) -> None:
    headers = {"Host": "localhost", **bearer(TOKEN)}
    for method, path in (("PUT", "/mcp/settings"), ("POST", "/mcp/tokens"), ("GET", "/mcp/calls")):
        response = await client.request(method, f"{API}{path}", headers=headers, json=None)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["error"]["code"] == "mcp_token_on_api"
    assert TOKEN not in (await client.get(f"{API}/mcp/settings", headers=headers)).text


async def test_call_429_journal_is_capped(
    mcp: Mcp,
    app: FastAPI,
    tools: FakeTools,
    inner: FakeDispatcher,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    install_gate(app, tools, inner, limits=Limits(calls_per_minute=1))
    token = await mcp.token()
    for _ in range(80):
        await mcp.call(token, "postings_list")

    async with db_session_factory() as db:
        calls = list((await db.execute(select(McpCall))).scalars())
    assert sum(1 for c in calls if c.code == 429) <= 30
    assert sum(1 for c in calls if c.code == 200) == 1


async def test_requests_of_any_method_are_throttled_before_any_write(
    mcp: Mcp,
    app: FastAPI,
    tools: FakeTools,
    inner: FakeDispatcher,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    install_gate(app, tools, inner, limits=Limits(requests_per_minute=3))
    token = await mcp.token()
    codes = [(await mcp.rpc(token, "ping")).status_code for _ in range(6)]

    assert codes == [200, 200, 200, 429, 429, 429]
    refused = await mcp.rpc(token, "ping")
    assert refused.json()["error"]["code"] == "rate_limited"
    assert int(refused.headers["retry-after"]) >= 1


async def test_last_used_is_written_at_most_once_a_minute(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token()

    async def last_used() -> datetime | None:
        async with db_session_factory() as db:
            return (await db.execute(select(McpToken.last_used_at))).scalar_one()

    await mcp.rpc(token, "ping")
    first = await last_used()
    await mcp.rpc(token, "ping")
    assert first is not None and await last_used() == first

    old = datetime.now(UTC) - timedelta(minutes=2)
    async with db_session_factory() as db:
        await db.execute(update(McpToken).values(last_used_at=old))
        await db.commit()
    await mcp.rpc(token, "ping")
    renewed = await last_used()
    assert renewed is not None and renewed > old + timedelta(minutes=1)


async def test_old_calls_are_purged(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    async with db_session_factory() as db:
        for days in (RETENTION_DAYS + 1, 1):
            db.add(
                McpCall(
                    user_id="u1",
                    token_id="t1",
                    action="postings_list",
                    level=1,
                    code=200,
                    created_at=now - timedelta(days=days),
                )
            )
        await db.commit()

    assert await purge_old_calls(db_session_factory, now) == 1

    async with db_session_factory() as db:
        left = list((await db.execute(select(McpCall))).scalars())
    assert len(left) == 1 and left[0].created_at > now - timedelta(days=2)


async def test_refusal_buckets_are_separate(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await mcp.token()  # l'utilisatrice locale existe ; l'interrupteur est allumé
    for i in range(40):  # 40 faux jetons : le seau « jeton inconnu » est plein
        fake = "tmcp_" + f"{i:02d}".ljust(43, "Z")
        await mcp.rpc(fake, "ping")
    await mcp.rpc(None, "ping", headers={"Host": "evil.example"})

    async with db_session_factory() as db:
        actions = [c.action for c in (await db.execute(select(McpCall))).scalars()]
    assert actions.count("refused:mcp_token_invalid") == 30
    assert "refused:host_not_allowed" in actions


def test_key_pattern_keeps_ordinary_words() -> None:
    for text in (
        "risk-assessment-framework",
        "task-based-learning-approach",
        "desk-research-methodology",
        "bearer representative-of-the-organisation",
    ):
        assert scrub_text(text) == text
        assert envelope({"t": text}, ())["data"] == {"t": text}
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in scrub_text("clé sk-ant-ABCDEFGHIJKLMNOPQRSTUV ok")
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in scrub_text("(sk-ABCDEFGHIJKLMNOPQRSTUV)")
    assert "abcdefghij1234567890" not in scrub_text("Authorization: Bearer abcdefghij1234567890x")


def test_log_filter_masks_mcp_tokens_and_keeps_words(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: [])
    logging.getLogger("t").error("jeton %s et risk-assessment-framework", TOKEN)
    assert TOKEN not in caplog.text and "risk-assessment-framework" in caplog.text


async def test_content_length_garbage_is_not_a_500() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    for value in ("²".encode("latin-1"), b"9" * 5000, b"-1", b"1.5"):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [(b"content-length", value)],
        }
        request = Request(scope, receive)
        try:
            body = await _read_body(request, 1_000)
        except AppError as exc:
            assert exc.status_code == 413  # trop gros
        else:
            assert body == b"{}"


def test_two_host_headers_are_refused() -> None:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": [(b"host", b"localhost"), (b"host", b"evil.example")],
    }
    with pytest.raises(AppError) as caught:
        check_local_origin(Request(scope))
    assert caught.value.status_code == 403
