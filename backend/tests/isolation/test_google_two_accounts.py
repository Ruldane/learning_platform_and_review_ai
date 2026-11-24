"""Deux comptes Google réels (cookies de session, faux fournisseur) : rien de ce que Camille crée
n'apparaît chez Dominique, ni dans une liste, ni par l'identifiant d'un objet (404) ; et chacun
garde ses propres valeurs pour les réglages et les clés. Le WebSocket de la session d'une autre est
refusé (4404) par `tests/realtime/test_ws_auth.py::test_websocket_of_another_account_session_is_
closed_4404` (mode Google, deux comptes réels) : il n'est pas refait ici."""

from datetime import date
from typing import Any

import httpx
from fastapi import FastAPI

from app.db.models.learning import Goal
from app.db.models.postings import JobPosting
from app.features.capture.service.journal import add_entry
from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.isolation.conftest import Browser

API = "/api/v1"
CAMILLE_KEY = "BSA-camille-4321"
DOMINIQUE_KEY = "BSA-dominique-8765"
CAMILLE_STYLE = "Style de Camille : phrases courtes."
DOMINIQUE_STYLE = "Style de Dominique : exemples d'abord."


async def _identity(client: httpx.AsyncClient) -> str:
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 200, r.text
    return str(r.json()["id"])


async def _seed_camille(app: FastAPI, camille: httpx.AsyncClient) -> dict[str, str]:
    """Un objectif, un élément de mémoire, une capture, une offre, un style et une clé : les
    identifiants des objets, pour les réclamer ensuite depuis l'autre compte."""
    me = await _identity(camille)
    async with app.state.session_factory() as db:
        goal = Goal(user_id=me, text="Devenir ingénieure en apprentissage automatique")
        posting = JobPosting(
            user_id=me, source="text", text="Offre de Camille", text_hash="h-camille",
            status="analyzing",
        )  # fmt: skip
        db.add_all([goal, posting])
        await db.flush()
        entry = await add_entry(
            db, me, kind="capture", text="Capture de Camille", occurred_on=date(2026, 11, 18),
            ref_key="camille-1",
        )  # fmt: skip
        await db.commit()
        ids = {"goal": goal.id, "posting": posting.id, "entry": entry}
    item = await camille.post(
        f"{API}/memory/items",
        json={"kind": "skill", "title": "Python de Camille", "text": "Je sais écrire des API."},
    )
    assert item.status_code == 201, item.text
    ids["item"] = item.json()["id"]
    settings = (await camille.get(f"{API}/settings")).json() | {"style_guide": CAMILLE_STYLE}
    assert (await camille.put(f"{API}/settings", json=settings)).status_code == 200
    keys = f"{API}/settings/api-keys"
    saved = await camille.post(keys, json={"provider": "brave", "key": CAMILLE_KEY})
    assert saved.status_code == 200, saved.text
    return ids


async def _brave(client: httpx.AsyncClient) -> dict[str, Any]:
    listed = (await client.get(f"{API}/settings/api-keys")).json()
    return next(k for k in listed if k["provider"] == "brave")  # type: ignore[no-any-return]


async def _assert_ids_unreachable(dominique: httpx.AsyncClient, ids: dict[str, str]) -> None:
    # Les identifiants de Camille ne mènent nulle part chez Dominique : 404 partout.
    for method, path, code in (
        ("GET", f"/goals/{ids['goal']}", "goal_not_found"),
        ("GET", f"/memory/items/{ids['item']}", "memory_item_not_found"),
        ("PATCH", f"/memory/items/{ids['item']}", "memory_item_not_found"),
        ("DELETE", f"/memory/items/{ids['item']}", "memory_item_not_found"),
        ("GET", f"/postings/{ids['posting']}", "posting_not_found"),
        ("DELETE", f"/postings/{ids['posting']}", "posting_not_found"),
        ("GET", f"/postings/{ids['posting']}/gap", "posting_not_found"),
    ):
        body = {"json": {"title": "Piraté"}} if method == "PATCH" else {}
        r = await dominique.request(method, f"{API}{path}", **body)
        assert (r.status_code, r.json()["error"]["code"]) == (404, code), (method, path)
    cursor = await dominique.get(f"{API}/journal", params={"before": ids["entry"]})
    assert cursor.status_code == 422  # le curseur d'une autre n'est pas le sien


async def _assert_writes_stay_private(
    camille: httpx.AsyncClient, dominique: httpx.AsyncClient, ids: dict[str, str]
) -> None:
    # Ce que fait Dominique n'atteint pas Camille : réglages et clés restent les leurs.
    own = (await dominique.get(f"{API}/settings")).json() | {"style_guide": DOMINIQUE_STYLE}
    assert (await dominique.put(f"{API}/settings", json=own)).status_code == 200
    keys = f"{API}/settings/api-keys"
    await dominique.post(keys, json={"provider": "brave", "key": DOMINIQUE_KEY})
    assert (await camille.get(f"{API}/settings")).json()["style_guide"] == CAMILLE_STYLE
    assert (await _brave(camille))["last4"] == "4321"
    assert (await _brave(dominique))["last4"] == "8765"
    assert (await dominique.get(f"{API}/memory/items")).json()["total"] == 0
    assert (await camille.get(f"{API}/memory/items/{ids['item']}")).status_code == 200  # intact
    assert len((await camille.get(f"{API}/goals")).json()) == 1

    # Aucune clé en clair, chez l'une comme chez l'autre.
    for client in (camille, dominique):
        text = (await client.get(f"{API}/settings/api-keys")).text
        assert CAMILLE_KEY not in text and DOMINIQUE_KEY not in text


async def test_google_two_accounts_never_see_each_other(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    assert await _identity(camille) != await _identity(dominique)
    ids = await _seed_camille(google_app, camille)

    # Les listes de Dominique sont vides, ses réglages sont les siens, sa clé n'existe pas.
    assert (await dominique.get(f"{API}/goals")).json() == []
    assert (await dominique.get(f"{API}/memory/items")).json() == {"items": [], "total": 0}
    assert (await dominique.get(f"{API}/journal")).json()["entries"] == []
    assert (await dominique.get(f"{API}/postings")).json() == []
    assert (await dominique.get(f"{API}/settings")).json()["style_guide"] == ""
    brave = await _brave(dominique)
    assert brave["source"] is None and brave["last4"] is None
    assert (await _brave(camille))["last4"] == "4321"

    await _assert_ids_unreachable(dominique, ids)
    await _assert_writes_stay_private(camille, dominique, ids)
