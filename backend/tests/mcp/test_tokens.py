"""Les jetons MCP : créés, hachés, montrés une fois, jamais journalisés, révocables."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpToken
from tests.mcp.support import API, Mcp


async def test_token_stored_hashed_and_shown_once(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    body = {"label": " Claude Code ", "features": ["postings", "Postings", "projects"]}
    created = await mcp.http.post(f"{API}/mcp/tokens", json=body)

    assert created.status_code == 201
    assert created.headers["cache-control"] == "no-store"
    data = created.json()
    plain = data["token"]
    assert plain.startswith("tmcp_") and len(plain) == 48
    assert data["label"] == "Claude Code" and data["mode"] == "read"  # lecture seule par défaut
    assert data["features"] == ["postings", "projects"]
    expires = datetime.fromisoformat(data["expires_at"])
    assert timedelta(days=29, hours=23) < expires - datetime.now(UTC) < timedelta(days=30, hours=1)

    async with db_session_factory() as db:
        rows = (await db.execute(select(McpToken))).scalars().all()
        assert len(rows) == 1
        assert rows[0].hash == hashlib.sha256(plain.encode()).hexdigest()
        everything = " ".join(str(v) for v in vars(rows[0]).values())
        assert plain not in everything
        dump = (await db.execute(text("select * from mcp_tokens"))).all()
        assert plain not in str(dump)

    listed = await mcp.http.get(f"{API}/mcp/tokens")
    assert plain not in listed.text and "token" not in listed.json()[0]
    assert "hash" not in listed.json()[0]


@pytest.mark.parametrize("days", [1, 7, 30, 90])
async def test_expiry_choices(mcp: Mcp, days: int) -> None:
    body = {"label": "x", "features": ["postings"], "expires_in_days": days}

    data = (await mcp.http.post(f"{API}/mcp/tokens", json=body)).json()

    left = datetime.fromisoformat(data["expires_at"]) - datetime.now(UTC)
    assert timedelta(days=days) - timedelta(minutes=5) < left <= timedelta(days=days)


@pytest.mark.parametrize(
    ("features", "status"),
    [
        (["mcp"], 422),
        (["postings", "auth"], 422),
        (["Pos tings"], 422),
        (["../etc"], 422),
        ([], 422),
    ],
)
async def test_never_exposed_and_invalid_features_are_refused(
    mcp: Mcp, features: list[str], status: int
) -> None:
    response = await mcp.http.post(f"{API}/mcp/tokens", json={"label": "x", "features": features})

    assert response.status_code == status
    assert (await mcp.http.get(f"{API}/mcp/tokens")).json() == []


async def test_bad_label_and_expiry_refused(mcp: Mcp) -> None:
    for body in (
        {"label": "   ", "features": ["postings"]},
        {"label": "x", "features": ["postings"], "expires_in_days": 365},
        {"label": "x", "features": ["postings"], "mode": "admin"},
    ):
        assert (await mcp.http.post(f"{API}/mcp/tokens", json=body)).status_code == 422


async def test_revoke_is_immediate_idempotent_and_keeps_the_row(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    token = await mcp.token()
    token_id = (await mcp.http.get(f"{API}/mcp/tokens")).json()[0]["id"]
    assert (await mcp.rpc(token, "ping")).status_code == 200

    assert (await mcp.http.delete(f"{API}/mcp/tokens/{token_id}")).status_code == 204
    first = (await mcp.http.get(f"{API}/mcp/tokens")).json()[0]["revoked_at"]
    assert first is not None
    assert (await mcp.http.delete(f"{API}/mcp/tokens/{token_id}")).status_code == 204
    assert (await mcp.http.get(f"{API}/mcp/tokens")).json()[0]["revoked_at"] == first
    assert (await mcp.rpc(token, "ping")).status_code == 401
    assert (await mcp.http.delete(f"{API}/mcp/tokens/inconnu")).status_code == 404
    async with db_session_factory() as db:
        assert len((await db.execute(select(McpToken))).scalars().all()) == 1


async def test_last_used_is_set_on_use(mcp: Mcp) -> None:
    token = await mcp.token()
    assert (await mcp.http.get(f"{API}/mcp/tokens")).json()[0]["last_used_at"] is None

    await mcp.rpc(token, "ping")

    assert (await mcp.http.get(f"{API}/mcp/tokens")).json()[0]["last_used_at"] is not None


async def test_token_never_logged(mcp: Mcp, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    token = await mcp.token(mode="write")
    await mcp.rpc(token, "initialize", {"protocolVersion": "2025-11-25"})
    await mcp.rpc(token, "tools/list")
    await mcp.call(token, "postings_add", {"title": "x"})
    await mcp.call(token, "projects_list")  # refusé : hors périmètre
    await mcp.call(token, "inconnu")
    await mcp.post(token, None, content=b"pas du json")
    await mcp.rpc(token, "ping", headers={"Host": "evil.example"})
    await mcp.http.post(f"/mcp?access_token={token}", content=b"{}", headers={"Host": "localhost"})
    await mcp.http.get(f"{API}/mcp/tokens")
    await mcp.http.delete(f"{API}/mcp/tokens/x")

    logged = caplog.text + " ".join(str(r.args) + r.getMessage() for r in caplog.records)
    assert token not in logged
    assert token[5:] not in logged
