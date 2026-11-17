"""Deux comptes Google réels (cookies de session, faux fournisseur) : rien de ce que Camille crée
n'apparaît chez Dominique, ni dans une liste, ni par l'identifiant d'un objet (404), ni par le
WebSocket de sa session ; et chacun garde ses propres valeurs pour les réglages et les clés."""

from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.models.learning import Goal
from app.db.models.postings import JobPosting
from app.features.capture.service.journal import add_entry
from app.main import create_app
from tests.features.auth.support import CAMILLE, DOMINIQUE, FakeGoogle, location_query
from tests.isolation.conftest import Browser
from tests.sessions_support import API as SESSIONS
from tests.sessions_support import use_test_runtime, wait_status_sync

API = "/api/v1"
CAMILLE_KEY = "BSA-camille-4321"
DOMINIQUE_KEY = "BSA-dominique-8765"
CAMILLE_STYLE = "Style de Camille : phrases courtes."
DOMINIQUE_STYLE = "Style de Dominique : exemples d'abord."
FRONT_ORIGIN = "http://localhost:5173"


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
        json={"kind": "acquis", "title": "Python de Camille", "text": "Je sais écrire des API."},
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
        text = (await client.get(keys)).text
        assert CAMILLE_KEY not in text and DOMINIQUE_KEY not in text


@pytest.fixture
def two_accounts_client(
    google_settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Client synchrone (WebSocket) sur l'app en mode Google, avec les parcours de test."""
    use_test_runtime(monkeypatch)
    app = create_app(
        google_settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    with TestClient(app) as client:
        fake = FakeGoogle(google_settings)
        fake.plug_into(client.app)  # type: ignore[arg-type]
        client.app.state.fake_google = fake  # type: ignore[attr-defined]
        yield client


def _sign_in(client: TestClient, email: str) -> str:
    fake: FakeGoogle = client.app.state.fake_google  # type: ignore[attr-defined]
    fake.email, fake.sub = email, f"sub-{email.split('@')[0]}"
    query = location_query(client.get("/api/v1/auth/google/login", follow_redirects=False))
    fake.nonce = query["nonce"]
    back = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "c", "state": query["state"]},
        follow_redirects=False,
    )
    assert back.status_code == 302 and back.headers["location"].endswith("/"), back.headers
    token = client.cookies.get("tremplin_session")
    assert token
    return token


def test_google_websocket_of_camille_session_is_refused_to_dominique(
    two_accounts_client: TestClient,
) -> None:
    client = two_accounts_client
    camille = _sign_in(client, CAMILLE)
    sid = client.post(SESSIONS, json={"graph": "one_llm_call"}).json()["session_id"]
    wait_status_sync(client, sid, "completed")
    headers = {"cookie": f"tremplin_session={camille}", "origin": FRONT_ORIGIN}
    with client.websocket_connect(f"{SESSIONS}/{sid}/stream", headers=headers) as ws:
        assert ws.receive_json()["seq"] == 1  # chez elle, le flux est là
    dominique = _sign_in(client, DOMINIQUE)
    assert dominique != camille
    assert client.get(f"{SESSIONS}/{sid}").status_code == 404
    headers = {"cookie": f"tremplin_session={dominique}", "origin": FRONT_ORIGIN}
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(f"{SESSIONS}/{sid}/stream", headers=headers) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 4404
