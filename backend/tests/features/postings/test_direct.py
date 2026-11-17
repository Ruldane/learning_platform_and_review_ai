"""Offre écrite en direct (10.W) : `POST /postings/direct` et `PATCH /postings/{id}` rangent le
texte et l'analyse de January ou de Claude comme le port de l'Analyste, sans agent ni appel au
modèle."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.memory import MemoryItem
from app.db.models.postings import JobPosting
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import API, LINK, ME
from tests.sessions_support import act_as
from tests.support.direct import OTHER, assert_no_agent
from tests.support.gap import analysis_data

SECRET = "SECRET-DE-L-OFFRE"


def body(**over: Any) -> dict[str, Any]:
    """Le corps d'une offre écrite en direct : l'analyse du jeu de test, sans son drapeau."""
    analysis = analysis_data()
    analysis.pop("is_job_posting")
    return {**analysis, "text": POSTING_TEXT, **over}


async def items(app: FastAPI) -> list[MemoryItem]:
    async with app.state.session_factory() as db:
        return list(
            (await db.execute(select(MemoryItem).where(MemoryItem.kind == "offre"))).scalars()
        )


async def test_write_posting_is_ready_with_memory_and_no_agent(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
) -> None:
    r = await client.post(f"{API}/postings/direct", json=body())

    assert r.status_code == 201, r.text
    created = r.json()
    assert created["created"] is True and created["session_id"] is None
    posting = created["posting"]
    assert (posting["status"], posting["source"], posting["title"]) == (
        "ready",
        "text",
        "AI Product Engineer",
    )
    assert posting["company"] == "Société Fictive" and posting["text"] == POSTING_TEXT.strip()
    assert posting["analysis"]["level"] == "confirme" and len(posting["analysis"]["keywords"]) == 4
    assert posting["gap_session_id"] is None and posting["score"] is None
    assert (await client.get(f"{API}/postings/{posting['id']}")).json()["title"] == posting["title"]
    [item] = await items(app)  # l'élément `offre`, écrit par January et indexé
    assert item.title == "AI Product Engineer — Société Fictive" and item.indexed_at is not None
    assert item.created_by == "user"
    async with app.state.session_factory() as db:
        row = (await db.execute(select(JobPosting))).scalar_one()
    assert row.memory_item_id == item.id and row.company_norm == "societe fictive"
    assert launcher_spy.started == []  # aucun graphe lancé
    await assert_no_agent(app)


async def test_same_text_or_same_link_returns_the_existing_posting(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    first = (await client.post(f"{API}/postings/direct", json=body())).json()["posting"]

    again = await client.post(f"{API}/postings/direct", json=body(title="Un autre titre"))

    assert again.status_code == 200 and again.json()["created"] is False
    assert (
        again.json()["posting"]["id"] == first["id"]
        and again.json()["posting"]["title"] == first["title"]
    )
    linked = await client.post(
        f"{API}/postings/direct", json=body(url=LINK, text=POSTING_TEXT + "\n.")
    )
    assert linked.status_code == 201 and linked.json()["posting"]["source"] == "url"
    same_link = await client.post(f"{API}/postings/direct", json=body(url=LINK + "?utm_source=x"))
    assert (
        same_link.status_code == 200
        and same_link.json()["posting"]["id"] == linked.json()["posting"]["id"]
    )
    async with app.state.session_factory() as db:
        assert len((await db.execute(select(JobPosting))).scalars().all()) == 2
    await assert_no_agent(app)


async def test_probable_duplicates_are_found_and_stored_on_both_sides(
    client: httpx.AsyncClient,
) -> None:
    first = (await client.post(f"{API}/postings/direct", json=body())).json()["posting"]

    second = await client.post(
        f"{API}/postings/direct", json=body(text=POSTING_TEXT + "\nAutre date de publication.")
    )

    assert second.status_code == 201
    levels = [(d["level"], d["posting_id"]) for d in second.json()["posting"]["duplicates"]]
    assert levels == [("probable", first["id"])]
    seen = (await client.get(f"{API}/postings/{first['id']}")).json()["duplicates"]
    assert [d["posting_id"] for d in seen] == [second.json()["posting"]["id"]]


async def test_patch_posting_updates_analysis_and_memory_title(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    posting = (await client.post(f"{API}/postings/direct", json=body())).json()["posting"]

    r = await client.patch(
        f"{API}/postings/{posting['id']}",
        json={"title": "Ingénieur IA", "company": "Autre Société", "location": "Paris"},
    )

    assert r.status_code == 200, r.text
    patched = r.json()
    assert (patched["title"], patched["company"]) == ("Ingénieur IA", "Autre Société")
    assert patched["analysis"]["location"] == "Paris" and patched["analysis"]["level"] == "confirme"
    assert patched["text"] == posting["text"] and patched["status"] == "ready"
    [item] = await items(app)  # mis à jour, pas dupliqué
    assert item.title == "Ingénieur IA — Autre Société"
    await assert_no_agent(app)


async def test_patch_of_an_unanalyzed_posting_is_refused(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    async with app.state.session_factory() as db:
        row = JobPosting(user_id=ME, source="text", text=POSTING_TEXT, text_hash="h1")
        db.add(row)
        await db.commit()
        posting_id = row.id
    act_as(app, ME)

    r = await client.patch(f"{API}/postings/{posting_id}", json={"title": "Un titre"})

    assert (r.status_code, r.json()["error"]["code"]) == (409, "posting_not_analyzed")


async def test_invalid_posting_is_422_without_echo(client: httpx.AsyncClient) -> None:
    trap = POSTING_TEXT + f"\n{SECRET}\n"
    calls = [
        body(text=SECRET),  # trop court
        body(keywords=[{"term": SECRET + "-absent", "variants": []}]),  # mot clé absent du texte
        body(requirements=[{"text": SECRET * 2, "required": True, "skills": []}]),
        body(level=SECRET),
        body(title=SECRET * 40),
        body(url="ftp://" + SECRET),
        body(url="http://u:p@exemple.org/" + SECRET),  # identifiants dans le lien
        {"text": trap},  # sans titre
    ]
    for payload in calls:
        r = await client.post(f"{API}/postings/direct", json=payload)
        assert r.status_code == 422 and SECRET not in r.text, payload
    codes = {
        (await client.post(f"{API}/postings/direct", json=p)).json()["error"]["code"]
        for p in calls[:2]
    }
    assert codes == {"posting_too_short", "posting_analysis_invalid"}
    posting = (await client.post(f"{API}/postings/direct", json=body())).json()["posting"]
    for patch in ({"keywords": [{"term": SECRET, "variants": []}]}, {"level": SECRET}, {}):
        r = await client.patch(f"{API}/postings/{posting['id']}", json=patch)
        assert r.status_code == 422 and SECRET not in r.text


async def test_posting_write_is_isolated_between_users(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    posting = (await client.post(f"{API}/postings/direct", json=body())).json()["posting"]
    act_as(app, OTHER)

    patched = await client.patch(f"{API}/postings/{posting['id']}", json={"title": "Pris"})
    mine = await client.post(
        f"{API}/postings/direct", json=body()
    )  # le même texte : une autre offre

    assert (patched.status_code, patched.json()["error"]["code"]) == (404, "posting_not_found")
    assert mine.status_code == 201 and mine.json()["posting"]["id"] != posting["id"]
    act_as(app, app.state.local_user_id)
    assert (await client.get(f"{API}/postings/{posting['id']}")).json()[
        "title"
    ] == "AI Product Engineer"
