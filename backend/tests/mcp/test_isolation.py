"""Isolation par utilisatrice : le jeton de A ne voit, ne gère et ne change rien de B."""

from collections.abc import Awaitable, Callable

import httpx
from fastapi import FastAPI

from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.mcp.support import API, FakeDispatcher, Mcp

Browser = Callable[[str], Awaitable[httpx.AsyncClient]]


async def make_token(browser: httpx.AsyncClient, label: str, mode: str = "write") -> dict[str, str]:
    await browser.put(f"{API}/mcp/settings", json={"enabled": True})
    response = await browser.post(
        f"{API}/mcp/tokens", json={"label": label, "features": ["postings"], "mode": mode}
    )
    assert response.status_code == 201, response.text
    data: dict[str, str] = response.json()
    return data


async def test_mcp_user_isolation(
    google_mcp: Mcp,
    google_client_factory: Browser,  # noqa: F811
    google_app: FastAPI,
    inner: FakeDispatcher,
) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    token_a = await make_token(camille, "Claude de Camille")
    token_b = await make_token(dominique, "Claude de Dominique")

    # Chaque jeton porte l'identité de sa propriétaire, et d'elle seule.
    await google_mcp.call(token_a["token"], "postings_add", {"title": "a"})
    await google_mcp.call(token_b["token"], "postings_list")
    owners = {name: identity.user_id for identity, name, _ in inner.calls}
    assert owners["postings_add"] != owners["postings_list"]
    assert {identity.token_id for identity, _, _ in inner.calls} == {token_a["id"], token_b["id"]}

    # Les jetons, le journal et l'interrupteur de B restent invisibles et intouchables pour A.
    assert [t["id"] for t in (await camille.get(f"{API}/mcp/tokens")).json()] == [token_a["id"]]
    assert [t["id"] for t in (await dominique.get(f"{API}/mcp/tokens")).json()] == [token_b["id"]]
    calls_a = (await camille.get(f"{API}/mcp/calls")).json()
    assert [(c["action"], c["token_id"]) for c in calls_a] == [("postings_add", token_a["id"])]
    calls_b = (await dominique.get(f"{API}/mcp/calls")).json()
    assert [(c["action"], c["token_id"]) for c in calls_b] == [("postings_list", token_b["id"])]

    assert (await camille.delete(f"{API}/mcp/tokens/{token_b['id']}")).status_code == 404
    assert (await google_mcp.rpc(token_b["token"], "ping")).status_code == 200

    await camille.put(f"{API}/mcp/settings", json={"enabled": False})
    assert (await google_mcp.rpc(token_a["token"], "ping")).status_code == 403
    assert (await google_mcp.rpc(token_b["token"], "ping")).status_code == 200  # B n'est pas coupée
    assert (await dominique.get(f"{API}/mcp/settings")).json() == {"enabled": True}
