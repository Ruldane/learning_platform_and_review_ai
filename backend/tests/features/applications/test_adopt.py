"""Lien version de CV ↔ candidature (SPEC 6.1 n° 1, D139) : la fiche « À postuler » née d'une
version prête, une seule fois, qui suit la plus récente tant qu'elle n'est pas postulée."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.service.adopt import adopt_versions
from app.features.applications.service.adopt_link import target_of
from tests.features.applications.conftest import API, add_posting, add_version, created_id
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


async def test_adopt_links_a_manual_application_without_posting(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """I1 : la fiche saisie à la main (même entreprise, intitulé proche) reçoit l'offre quand sa
    version est prête, au lieu qu'une seconde fiche naisse."""
    manual = await created_id(client, company="Société Fictive", title="Développeuse IA")
    posting = await add_posting(app, text="Le texte collé plus tard.")
    version = await add_version(app, posting)
    listed = (await client.get(API)).json()
    assert [a["id"] for a in listed] == [manual]
    assert (listed[0]["posting_id"], listed[0]["cv_version_id"]) == (posting, version)
    detail = (await client.get(f"{API}/{manual}")).json()
    assert detail["posting_text"] == "Le texte collé plus tard."
    assert (await client.get(API)).json() == listed  # rejouée : rien de plus


async def test_adopt_links_by_same_link(client: httpx.AsyncClient, app: FastAPI) -> None:
    url = "https://jobs.example.org/offres/lien-commun"
    manual = await created_id(client, company="Autre SA", title="Tout autre intitulé", url=url)
    posting = await add_posting(app, company="Société Fictive", title="Développeuse IA", url=url)
    await add_version(app, posting)
    listed = (await client.get(API)).json()
    assert [(a["id"], a["posting_id"]) for a in listed] == [(manual, posting)]


async def test_adopt_keeps_a_postulated_manual_application_version_frozen(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    manual = await created_id(client, company="Société Fictive", title="Développeuse IA")
    await client.post(f"{API}/{manual}/events", json={"kind": "status", "status": "applied"})
    posting = await add_posting(app)
    version = await add_version(app, posting)
    [fiche] = (await client.get(API)).json()
    assert (fiche["id"], fiche["posting_id"], fiche["cv_version_id"]) == (manual, posting, version)
    detail = (await client.get(f"{API}/{manual}")).json()
    assert "version" in [e["kind"] for e in detail["events"]]


async def test_adopt_never_steals_an_application_linked_to_another_posting(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    [first] = (await client.get(API)).json()
    other = await add_posting(app, url="https://jobs.example.org/offres/autre-lien")
    await add_version(app, other)
    listed = (await client.get(API)).json()
    assert [(a["id"], a["posting_id"]) for a in listed] == [(first["id"], posting)]


async def test_adopt_skips_an_application_confirmed_distinct(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    manual = await created_id(client, company="Société Fictive", title="Développeuse IA")
    posting = await add_posting(app)
    async with app.state.session_factory() as db:
        row = await db.get(Application, manual)
        assert row is not None
        row.distinct_from = [posting]
        await db.commit()
    await add_version(app, posting)
    listed = (await client.get(API)).json()
    assert {a["posting_id"] for a in listed} == {None, posting} and len(listed) == 2


def test_adopt_link_certain_beats_probable() -> None:
    """Un hit certain vers une fiche déjà liée à une autre offre : aucun lien, même si une fiche
    sans offre ressemble (probable) ; sans hit certain, la fiche sans offre est reliée."""
    zone, today = ZoneInfo("Europe/Paris"), date(2026, 11, 15)
    moment = datetime(2026, 11, 1, tzinfo=UTC)
    url = "https://jobs.example.org/offres/lien"
    posting = JobPosting(
        id="p-new", user_id="moi", url=url, url_norm=url, company="Société Fictive",
        title="Développeuse IA", source="url", text="t", text_hash="h", duplicates=[],
    )  # fmt: skip

    def row(row_id: str, **over: object) -> Application:
        fields: dict[str, object] = {
            "user_id": "moi", "company": "Société Fictive", "company_norm": "societe fictive",
            "title": "Développeuse IA", "status": "to_apply", "created_at": moment,
            "distinct_from": [],
        }  # fmt: skip
        return Application(id=row_id, **(fields | over))

    elsewhere = row("elsewhere", posting_id="p-other", url_norm=url, title="Autre titre")
    free = row("free", posting_id=None)
    assert target_of(posting, [elsewhere, free], zone, today) == (None, True)
    assert target_of(posting, [free], zone, today) == (free, True)
    same_link = row("same-link", posting_id=None, url_norm=url, title="Autre titre")
    assert target_of(posting, [same_link, free], zone, today) == (same_link, True)


async def test_linking_applied_card_says_linked_not_sent(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """La fiche postulée à la main est reliée à une version peut-être postérieure à sa candidature :
    l'événement dit « liée à la fiche », pas « envoyée » (« envoyée » reste pour le passage à
    « Postulée »)."""
    manual = await created_id(client, company="Société Fictive", title="Développeuse IA")
    await client.post(f"{API}/{manual}/events", json={"kind": "status", "status": "applied"})
    posting = await add_posting(app)
    version = await add_version(app, posting, number=2)
    await client.get(API)  # la liste adopte les versions prêtes
    detail = (await client.get(f"{API}/{manual}")).json()
    [event] = [e for e in detail["events"] if e["kind"] == "version"]
    assert (event["ref_id"], event["text"]) == (version, "CV version 2 linked to the record.")
