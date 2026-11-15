"""Lien version de CV ↔ candidature (SPEC 6.1 n° 1, D139) : la fiche « À postuler » née d'une
version prête, une seule fois, qui suit la plus récente tant qu'elle n'est pas postulée."""

import httpx
from fastapi import FastAPI

from app.features.applications.service.adopt import adopt_versions
from tests.features.applications.conftest import API, add_posting, add_version
from tests.sessions_support import act_as


async def test_adopt_creates_to_apply_once(
    client: httpx.AsyncClient, posting: str, ready_version: str
) -> None:
    first = (await client.get(API)).json()
    second = (await client.get(API)).json()
    assert len(first) == 1 and first == second
    [fiche] = first
    assert (fiche["status"], fiche["posting_id"], fiche["cv_version_id"]) == (
        "to_apply",
        posting,
        ready_version,
    )
    assert (fiche["company"], fiche["title"]) == ("Société Fictive", "Développeuse IA")
    detail = (await client.get(f"{API}/{fiche['id']}")).json()
    assert [e["kind"] for e in detail["events"]] == ["created"]
    assert detail["posting_text"].startswith("Texte de l'offre fictive")


async def test_adopt_follows_latest_version_while_to_apply(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    await client.get(API)
    newer = await add_version(app, posting, number=2)
    [fiche] = (await client.get(API)).json()
    assert (fiche["cv_version_id"], fiche["cv_version_number"]) == (newer, 2)


async def test_adopt_ignores_versions_not_ready(
    client: httpx.AsyncClient, app: FastAPI, posting: str
) -> None:
    await add_version(app, posting, status="rendering")
    assert (await client.get(API)).json() == []


async def test_adopt_leaves_a_withdrawn_application_alone(
    client: httpx.AsyncClient, posting: str, ready_version: str
) -> None:
    [fiche] = (await client.get(API)).json()
    r = await client.post(
        f"{API}/{fiche['id']}/events", json={"kind": "status", "status": "withdrawn"}
    )
    assert r.status_code == 200
    listed = (await client.get(API)).json()
    assert [a["id"] for a in listed] == [fiche["id"]] and listed[0]["status"] == "withdrawn"


async def test_adopt_uses_an_existing_manual_application(
    client: httpx.AsyncClient, posting: str, ready_version: str
) -> None:
    created = await client.post(API, json={"posting_id": posting})
    assert created.status_code == 201
    listed = (await client.get(API)).json()
    assert [a["id"] for a in listed] == [created.json()["application"]["id"]]


async def test_adopt_is_per_user_and_stats_adopt_too(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    """Chaque utilisatrice a son offre et sa version prête : chacune n'adopte que la sienne."""
    other_user = "autre-utilisatrice"
    theirs = await add_posting(app, company="Autre SA", title="Poste", user_id=other_user)
    their_version = await add_version(app, theirs, user_id=other_user)
    stats = (await client.get(f"{API}/stats")).json()  # adopte avant de compter
    assert stats["by_status"]["to_apply"] == 1
    [mine] = (await client.get(API)).json()
    assert (mine["posting_id"], mine["cv_version_id"]) == (posting, ready_version)
    act_as(app, other_user)
    [hers] = (await client.get(API)).json()
    assert (hers["posting_id"], hers["cv_version_id"], hers["company"]) == (
        theirs,
        their_version,
        "Autre SA",
    )
    async with app.state.session_factory() as db:
        assert await adopt_versions(db, other_user) == 0  # déjà adoptée
        assert await adopt_versions(db, "troisieme-utilisatrice") == 0  # rien à elle
        await db.commit()
