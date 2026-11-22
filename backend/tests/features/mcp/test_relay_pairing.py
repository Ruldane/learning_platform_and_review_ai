"""Un code d'interface appaire un relais une fois et ouvre les parcours déclarés."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.mcp import McpToken

ROOT = "/api/v1/mcp"
PAIRING = f"{ROOT}/relay/pairing"
EXCHANGE = f"{ROOT}/relay/exchange"
STATUS = f"{ROOT}/relay/status"
HOST = {"Host": "localhost:8000"}


async def start(client: httpx.AsyncClient) -> str:
    started = await client.post(PAIRING, headers=HOST)
    assert started.status_code == 201, started.text
    assert started.headers["Cache-Control"] == "no-store"
    return str(started.json()["code"])


async def test_code_exchange_is_single_use_and_renewal_replaces_token(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    await client.put(f"{ROOT}/settings", headers=HOST, json={"enabled": True})
    code = await start(client)
    pending = await client.get(STATUS, headers=HOST)
    assert pending.json() == {"state": "pending", "missing_features": []}
    assert code not in pending.text
    attempts = await asyncio.gather(
        *[client.post(EXCHANGE, json={"code": code}, headers=HOST) for _ in range(2)]
    )
    assert sorted(response.status_code for response in attempts) == [201, 401]
    exchanged = next(response for response in attempts if response.status_code == 201)
    assert exchanged.headers["Cache-Control"] == "no-store"
    token = exchanged.json()["token"]
    listed = (await client.get(f"{ROOT}/tokens", headers=HOST)).json()
    assert len(listed) == 1 and listed[0]["mode"] == "write"
    assert set(listed[0]["features"]) == {
        "sessions",
        *app.state.mcp_registry.graph_features.values(),
    }
    paired = await client.get(STATUS, headers=HOST)
    assert paired.json() == {"state": "paired", "missing_features": []}
    assert code not in paired.text and token not in paired.text

    renewed = await client.post(EXCHANGE, json={"code": await start(client)}, headers=HOST)
    assert renewed.status_code == 201 and renewed.json()["token"] != token
    listed = (await client.get(f"{ROOT}/tokens", headers=HOST)).json()
    assert len(listed) == 2 and sum(row["revoked_at"] is not None for row in listed) == 1
    assert (await client.delete(PAIRING, headers=HOST)).status_code == 204
    assert (await client.get(STATUS, headers=HOST)).json()["state"] == "revoked"


async def test_status_distinguishes_incomplete_scope_revocation_and_expiry(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    await client.put(f"{ROOT}/settings", headers=HOST, json={"enabled": True})
    code = await start(client)
    assert (await client.post(EXCHANGE, json={"code": code}, headers=HOST)).status_code == 201
    async with app.state.session_factory() as db:
        await db.execute(update(McpToken).values(features=["sessions"]))
        await db.commit()
    incomplete = (await client.get(STATUS, headers=HOST)).json()
    assert incomplete == {
        "state": "incomplete",
        "missing_features": sorted(
            set(app.state.mcp_registry.graph_features.values()) - {"sessions"}
        ),
    }
    async with app.state.session_factory() as db:
        await db.execute(update(McpToken).values(expires_at=datetime.now(UTC) - timedelta(hours=1)))
        await db.commit()
    assert (await client.get(STATUS, headers=HOST)).json()["state"] == "expired"


async def test_expired_or_cancelled_code_never_issues_a_token(
    client: httpx.AsyncClient, monkeypatch
) -> None:
    await client.put(f"{ROOT}/settings", headers=HOST, json={"enabled": True})
    code = await start(client)
    from app.features.mcp.service import relay_pairing

    later = datetime.now(UTC) + timedelta(minutes=3)
    monkeypatch.setattr(relay_pairing, "utcnow", lambda: later)
    expired = await client.post(EXCHANGE, json={"code": code}, headers=HOST)
    assert expired.status_code == 401 and code not in expired.text
    assert (await client.get(STATUS, headers=HOST)).json()["state"] == "expired"
    code = await start(client)
    assert (await client.delete(PAIRING, headers=HOST)).status_code == 204
    assert (await client.post(EXCHANGE, json={"code": code}, headers=HOST)).status_code == 401
    assert (await client.get(f"{ROOT}/tokens", headers=HOST)).json() == []


async def test_exchange_rejects_browser_origins_and_refusal_does_not_use_the_code(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.post(PAIRING, headers=HOST)).status_code == 403
    await client.put(f"{ROOT}/settings", headers=HOST, json={"enabled": True})
    code = await start(client)
    refused = await client.post(
        EXCHANGE, json={"code": code}, headers={**HOST, "Origin": "http://localhost:5173"}
    )
    assert refused.status_code == 403 and code not in refused.text
    assert (await client.post(EXCHANGE, json={"code": code}, headers=HOST)).status_code == 201
