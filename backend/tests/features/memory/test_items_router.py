"""API REST des éléments de la mémoire (14.2) : CRUD, filtres, recherche, isolation, erreurs."""

from typing import Any

import httpx
from fastapi import FastAPI

from tests.sessions_support import act_as

API = "/api/v1/memory/items"
SEARCH = "/api/v1/memory/search"


async def _create(client: httpx.AsyncClient, **fields: Any) -> dict[str, Any]:
    body = {"kind": "acquis", "title": "Python", "text": "Je sais écrire des scripts.", **fields}
    r = await client.post(API, json=body)
    assert r.status_code == 201, r.text
    created: dict[str, Any] = r.json()
    return created


async def test_items_crud_roundtrip(client: httpx.AsyncClient) -> None:
    created = await _create(client, tags=["python"])
    assert created["created_by"] == "user" and created["level"] == "declare"
    assert created["status"] == "active" and created["indexed"] is True
    listing = (await client.get(API)).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == created["id"]

    patched = await client.patch(
        f"{API}/{created['id']}",
        json={"text": "Je sais écrire des scripts et des API.", "level": "en_cours"},
    )
    assert patched.status_code == 200
    assert patched.json()["level"] == "en_cours" and "des API" in patched.json()["text"]

    detail = (await client.get(f"{API}/{created['id']}")).json()
    assert [c["ordinal"] for c in detail["chunks"]] == [0]
    assert [w["action"] for w in detail["writes"]] == ["update", "create"]
    assert {w["author"] for w in detail["writes"]} == {"user"} and detail["neighbors"] == []

    found = (await client.post(SEARCH, json={"query": "scripts API"})).json()
    assert [h["item_id"] for h in found["hits"]] == [created["id"]]
    assert found["agent_text"].startswith("Mémoire — 1 fragment(s) pour « scripts API » :")

    assert (await client.delete(f"{API}/{created['id']}")).status_code == 204
    gone = await client.get(f"{API}/{created['id']}")
    assert gone.status_code == 404 and gone.json()["error"]["code"] == "memory_item_not_found"
    assert (await client.get(API)).json() == {"items": [], "total": 0}
    assert (await client.post(SEARCH, json={"query": "scripts"})).json()["hits"] == []


async def test_items_isolated_between_users(app: FastAPI, client: httpx.AsyncClient) -> None:
    mine = await _create(client)
    act_as(app, "autre")
    assert (await client.get(API)).json() == {"items": [], "total": 0}
    for method, url, kwargs in (
        ("GET", f"{API}/{mine['id']}", {}),
        ("PATCH", f"{API}/{mine['id']}", {"json": {"title": "Piraté"}}),
        ("DELETE", f"{API}/{mine['id']}", {}),
    ):
        r = await client.request(method, url, **kwargs)
        assert r.status_code == 404 and r.json()["error"]["code"] == "memory_item_not_found"
    assert (await client.post(SEARCH, json={"query": "scripts"})).json()["hits"] == []
    twin = await _create(client)  # même contenu chez l'autre : un autre élément
    assert twin["id"] != mine["id"]
    app.dependency_overrides.clear()
    assert (await client.get(f"{API}/{mine['id']}")).status_code == 200  # intact chez le premier
    assert (await client.get(API)).json()["total"] == 1


async def test_list_filters(client: httpx.AsyncClient) -> None:
    await _create(client, title="Python", tags=["python", "web"])
    await _create(client, kind="decision", title="Cap", text="Viser Paris.", tags=["carrière"])
    await _create(client, kind="offre", title="Offre", text="Poste.", tags=["python"])

    async def titles(**params: Any) -> list[str]:
        r = await client.get(API, params=params)
        assert r.status_code == 200, r.text
        return [i["title"] for i in r.json()["items"]]

    assert await titles(kind="acquis") == ["Python"]
    assert sorted(await titles(tag="python")) == ["Offre", "Python"]
    assert len(await titles(author="user")) == 3 and await titles(author="writer") == []
    assert await titles(status="pending") == []
    assert len(await titles(limit=1, offset=1)) == 1
    assert (await client.get(API, params={"limit": 1})).json()["total"] == 3


async def test_list_dates_are_inclusive_bounds(client: httpx.AsyncClient) -> None:
    created = await _create(client)
    moment = created["created_at"]
    for params in ({"since": moment}, {"until": moment}, {"since": moment, "until": moment}):
        assert (await client.get(API, params=params)).json()["total"] == 1
    assert (await client.get(API, params={"since": "2100-01-01T00:00:00Z"})).json()["total"] == 0
    assert (await client.get(API, params={"until": "2000-01-01"})).json()["total"] == 0
    # Une date sans fuseau est lue en UTC.
    assert (await client.get(API, params={"since": "2000-01-01T00:00:00"})).json()["total"] == 1


async def test_list_rejects_bad_parameters(client: httpx.AsyncClient) -> None:
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"kind": "nope"}, {"status": "x"}):
        assert (await client.get(API, params=params)).status_code == 422


async def test_422_never_echoes_input(client: httpx.AsyncClient) -> None:
    r = await client.post(API, json={"kind": "acquis", "title": "SECRET-VALUE" * 50, "text": "x"})
    assert r.status_code == 422 and "SECRET-VALUE" not in r.text
    r = await client.post(API, json={"kind": "SECRET-KIND", "title": "t", "text": "x"})
    assert r.status_code == 422 and "SECRET-KIND" not in r.text
    r = await client.post(SEARCH, json={"query": "SECRET-VALUE" * 50})
    assert r.status_code == 422 and "SECRET-VALUE" not in r.text
    r = await client.patch(f"{API}/x", json={"status": "SECRET-STATUS"})
    assert r.status_code == 422 and "SECRET-STATUS" not in r.text


async def test_user_cannot_create_lecons_sources_or_documents(client: httpx.AsyncClient) -> None:
    for kind in ("lecon", "source", "document"):
        r = await client.post(API, json={"kind": kind, "title": "t", "text": "x"})
        assert r.status_code == 422


async def test_patch_cannot_set_a_high_level_or_pending(client: httpx.AsyncClient) -> None:
    created = await _create(client)
    for body in ({"level": "valide"}, {"status": "pending"}, {"tags": ["x"] * 11}):
        assert (await client.patch(f"{API}/{created['id']}", json=body)).status_code == 422


async def test_duplicate_update_is_a_409_and_blank_search_a_422(client: httpx.AsyncClient) -> None:
    await _create(client, kind="offre", title="A", text="Premier poste.")
    other = await _create(client, kind="offre", title="B", text="Second poste.")
    r = await client.patch(f"{API}/{other['id']}", json={"text": "premier POSTE."})
    assert r.status_code == 409 and r.json()["error"]["code"] == "memory_duplicate"
    blank = await client.post(SEARCH, json={"query": "   "})
    assert blank.status_code == 422 and blank.json()["error"]["code"] == "memory_query_empty"
    assert (await client.post(SEARCH, json={"query": ""})).status_code == 422
    assert (await client.post(SEARCH, json={"query": "x", "k": 0})).status_code == 422
    assert (await client.post(SEARCH, json={"query": "x", "k": 51})).status_code == 422


async def test_unauthenticated_requests_are_refused(client_google_mode: httpx.AsyncClient) -> None:
    assert (await client_google_mode.get(API)).status_code == 401
    assert (await client_google_mode.post(SEARCH, json={"query": "x"})).status_code == 401
