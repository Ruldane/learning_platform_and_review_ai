"""La porte du MCP : jeton absent, expiré, révoqué, inconnu ; périmètre et mode ; interrupteur ;
origine ; jamais d'accès croisé entre cookie et jeton."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.core.deps import CurrentUser, get_current_user, get_interface_user
from app.core.errors import AppError
from app.db.models.mcp import McpToken
from tests.features.auth.support import CAMILLE
from tests.mcp.support import API, FakeDispatcher, Mcp, bearer

Browser = Callable[[str], Awaitable[httpx.AsyncClient]]
FORGED = "tmcp_" + "A" * 43


async def expire(factory: async_sessionmaker[AsyncSession], **values: datetime) -> None:
    async with factory() as db:
        await db.execute(update(McpToken).values(**values))
        await db.commit()


async def test_missing_expired_revoked_unknown_token_is_401(
    mcp: Mcp, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    good = await mcp.token()
    assert (await mcp.rpc(good, "ping")).status_code == 200

    missing = await mcp.rpc(None, "ping")
    unknown = await mcp.rpc(FORGED, "ping")
    malformed = await mcp.rpc("pas-un-jeton", "ping")
    wrong_scheme = await mcp.rpc(None, "ping", headers={"Authorization": f"Basic {good}"})
    twice = await mcp.http.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers=[
            ("Host", "localhost"),
            ("Authorization", f"Bearer {good}"),
            ("Authorization", f"Bearer {good}"),
        ],
    )
    in_query = await mcp.http.post(
        f"/mcp?token={good}&access_token={good}",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Host": "localhost"},
    )
    for response in (missing, unknown, malformed, wrong_scheme, twice, in_query):
        assert response.status_code == 401, response.text
        assert response.json()["error"]["code"] == "mcp_token_invalid"
        assert response.headers["www-authenticate"].startswith("Bearer")

    await expire(db_session_factory, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    expired = await mcp.rpc(good, "ping")
    assert expired.status_code == 401 and expired.json()["error"]["code"] == "mcp_token_expired"

    await expire(db_session_factory, expires_at=datetime.now(UTC) + timedelta(days=1))
    assert (await mcp.rpc(good, "ping")).status_code == 200
    listed = (await mcp.http.get(f"{API}/mcp/tokens")).json()
    revoke = await mcp.http.delete(f"{API}/mcp/tokens/{listed[0]['id']}")
    assert revoke.status_code == 204
    revoked = await mcp.rpc(good, "ping")
    assert revoked.status_code == 401 and revoked.json()["error"]["code"] == "mcp_token_revoked"


async def test_read_token_cannot_call_write_tool(mcp: Mcp, inner: FakeDispatcher) -> None:
    read = await mcp.token(mode="read")

    assert (await mcp.call(read, "postings_list")).status_code == 200
    for tool in ("postings_add", "postings_delete"):
        response = await mcp.call(read, tool)
        assert response.status_code == 403, tool
        assert response.json()["error"]["code"] == "write_not_allowed"
    assert [name for _, name, _ in inner.calls] == ["postings_list"]

    write = await mcp.token(mode="write")
    assert (await mcp.call(write, "postings_add")).status_code == 200


async def test_feature_outside_scope_is_403(mcp: Mcp, inner: FakeDispatcher) -> None:
    token = await mcp.token(features=("postings",), mode="write")

    response = await mcp.call(token, "projects_list")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "feature_not_allowed"
    assert inner.calls == []


async def test_kill_switch_refuses_everything_and_is_off_by_default(
    mcp: Mcp, inner: FakeDispatcher
) -> None:
    assert (await mcp.http.get(f"{API}/mcp/settings")).json() == {"enabled": False}
    token = await mcp.token(enable=False)

    for method in ("initialize", "ping", "tools/list", "tools/call"):
        response = await mcp.rpc(token, method, {"name": "postings_list"})
        assert response.status_code == 403, method
        assert response.json()["error"]["code"] == "mcp_disabled"
    assert inner.calls == []

    await mcp.enable(True)
    assert (await mcp.rpc(token, "ping")).status_code == 200
    await mcp.enable(False)
    assert (await mcp.rpc(token, "ping")).status_code == 403
    assert (await mcp.http.get(f"{API}/mcp/settings")).json() == {"enabled": False}


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({"Host": "evil.example"}, "host_not_allowed"),
        ({"Host": "localhost.evil.example"}, "host_not_allowed"),
        ({"Host": "evil@localhost"}, "host_not_allowed"),
        ({"Host": "192.168.1.20:8000"}, "host_not_allowed"),
        ({"Host": "localhost", "Origin": "https://evil.example"}, "origin_not_allowed"),
        ({"Host": "localhost", "Origin": "null"}, "origin_not_allowed"),
        ({"Host": "localhost", "Origin": "http://localhost.evil.example"}, "origin_not_allowed"),
        (
            {"Host": "localhost", "Origin": "http://127.0.0.1:5173@evil.example"},
            "origin_not_allowed",
        ),
    ],
)
async def test_non_local_origin_or_host_refused(
    mcp: Mcp, inner: FakeDispatcher, headers: dict[str, str], code: str
) -> None:
    token = await mcp.token(mode="write")

    response = await mcp.rpc(token, "tools/call", {"name": "postings_add"}, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == code
    assert inner.calls == []


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "localhost:8000"},
        {"Host": "127.0.0.1:8000"},
        {"Host": "localhost", "Origin": "http://localhost:5173"},
        {"Host": "127.0.0.1", "Origin": "http://127.0.0.1:8000"},
    ],
)
async def test_local_origin_and_host_accepted(mcp: Mcp, headers: dict[str, str]) -> None:
    token = await mcp.token()

    assert (await mcp.rpc(token, "ping", headers=headers)).status_code == 200


async def test_bearer_on_api_v1_is_ignored(
    google_mcp: Mcp,
    google_client_factory: Browser,
    google_app: FastAPI,  # noqa: F811
) -> None:
    """Mode Google : le jeton ouvre `/mcp`, jamais `/api/v1`."""
    browser = await google_client_factory(CAMILLE)
    created = await browser.post(
        f"{API}/mcp/tokens", json={"label": "Claude Code", "features": ["postings"]}
    )
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    await browser.put(f"{API}/mcp/settings", json={"enabled": True})
    assert (await google_mcp.rpc(token, "ping")).status_code == 200

    for method, path in (
        ("GET", "/mcp/tokens"),
        ("GET", "/mcp/settings"),
        ("GET", "/postings"),
        ("GET", "/settings"),
        ("POST", "/mcp/tokens"),
        ("DELETE", "/mcp/tokens/x"),
    ):
        response = await google_mcp.http.request(
            method, f"{API}{path}", headers=bearer(token), json=None
        )
        if path.startswith("/mcp"):  # un jeton rejoué sur les réglages de l'interface : refusé
            assert response.status_code == 403, (method, path, response.text)
            assert response.json()["error"]["code"] == "mcp_token_on_api"
        else:  # ailleurs : ignoré, donc 401 sans cookie
            assert response.status_code == 401, (method, path, response.text)
            assert response.json()["error"]["code"] == "auth_required"


async def test_session_cookie_on_mcp_is_ignored(
    google_mcp: Mcp,
    google_client_factory: Browser,
    google_app: FastAPI,  # noqa: F811
) -> None:
    browser = await google_client_factory(CAMILLE)
    await browser.put(f"{API}/mcp/settings", json={"enabled": True})
    assert (await browser.get(f"{API}/mcp/settings")).status_code == 200

    response = await browser.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"Host": "localhost"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "mcp_token_invalid"


async def test_mcp_identity_cannot_be_forged_by_header_or_cookie(
    google_client_factory: Browser,
    google_app: FastAPI,  # noqa: F811
) -> None:
    transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
    forged = {
        "X-Mcp-Identity": "u1",
        "Mcp-Identity": '{"user_id": "u1"}',
        "X-User-Id": "u1",
        "X-Forwarded-User": "u1",
        "Cookie": "mcp_identity=u1; mcp_token_id=t1; MCP_IDENTITY=u1",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anonymous:
        for path in ("/postings", "/settings", "/mcp/tokens", "/mcp/calls", "/ide/exercises"):
            response = await anonymous.get(f"{API}{path}", headers=forged)
            assert response.status_code == 401, path
    assert MCP_IDENTITY.get() is None


async def test_get_current_user_reads_only_the_identity_posed_by_the_dispatcher() -> None:
    identity = McpIdentity(
        user_id="owner-1", token_id="t1", label="Claude", features=frozenset(), mode="read"
    )

    class Conn:  # un appel qui ne porte aucun cookie
        class url:  # noqa: N801
            path = "/api/v1/applications"

        class app:  # noqa: N801
            class state:  # noqa: N801
                authenticator = None

    reset = MCP_IDENTITY.set(identity)
    try:
        user = await get_current_user(Conn())  # type: ignore[arg-type]
        assert user == CurrentUser(id="owner-1", email=None)
        with pytest.raises(AppError) as refused:  # l'interface seule gère les jetons
            await get_interface_user(Conn())  # type: ignore[arg-type]
        assert refused.value.status_code == 403
    finally:
        MCP_IDENTITY.reset(reset)


async def test_token_routes_need_cookie_not_token(
    google_mcp: Mcp,
    google_client_factory: Browser,
    google_app: FastAPI,  # noqa: F811
) -> None:
    browser = await google_client_factory(CAMILLE)
    created = await browser.post(
        f"{API}/mcp/tokens",
        json={"label": "Claude Code", "features": ["postings"], "mode": "write"},
    )
    token = created.json()["token"]

    with_token = await google_mcp.http.post(
        f"{API}/mcp/tokens",
        json={"label": "Autre", "features": ["postings"]},
        headers=bearer(token),
    )
    assert with_token.status_code == 403
    assert with_token.json()["error"]["code"] == "mcp_token_on_api"
    listed = await browser.get(f"{API}/mcp/tokens")
    assert [item["label"] for item in listed.json()] == ["Claude Code"]


async def test_removed_account_loses_its_tokens(
    google_mcp: Mcp,
    google_client_factory: Browser,
    google_app: FastAPI,  # noqa: F811
) -> None:
    browser = await google_client_factory(CAMILLE)
    created = await browser.post(f"{API}/mcp/tokens", json={"label": "A", "features": ["postings"]})
    token = created.json()["token"]
    await browser.put(f"{API}/mcp/settings", json={"enabled": True})
    assert (await google_mcp.rpc(token, "ping")).status_code == 200

    google_app.state.settings.allowed_emails = "quelqu-un-d-autre@example.org"

    response = await google_mcp.rpc(token, "ping")
    assert response.status_code == 401
