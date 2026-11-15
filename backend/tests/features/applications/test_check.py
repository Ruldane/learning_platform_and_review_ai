"""Contrôle à l'entrée d'une offre (SPEC 5.3, 6.3, D139) : par offre (sa fiche, les alertes, les
informations), par lien avant l'analyse (« certain » seulement)."""

import httpx
from fastapi import FastAPI

from tests.features.applications.conftest import API, add_posting, create, created_id


async def _check(client: httpx.AsyncClient, **params: str) -> httpx.Response:
    return await client.get(f"{API}/check", params=params)


async def test_check_by_posting_returns_own_and_alerts(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    mine = await add_posting(app, title="Développeuse IA")
    own = await created_id(client, posting_id=mine, status="applied", applied_on="2026-11-03")
    twin = await add_posting(app, title="Développeuse IA (H/F)")
    r = await _check(client, posting_id=twin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["own"] is None and body["info"] == []
    [alert] = body["alerts"]
    assert (alert["level"], alert["application_id"]) == ("probable", own)
    assert "le 3 novembre" in alert["message"] and "Postulée" in alert["message"]
    r = await _check(client, posting_id=mine)  # sa propre fiche n'est pas un doublon
    assert r.json()["alerts"] == []
    assert r.json()["own"] == {
        "id": own,
        "company": "Société Fictive",
        "title": "Développeuse IA",
        "status": "applied",
        "applied_on": "2026-11-03",
    }


async def test_check_by_posting_reports_info_and_possible(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    other = await add_posting(app, title="Responsable Marketing")
    first = await created_id(client, posting_id=other)
    elsewhere = await add_posting(app, title="Développeuse IA")
    body = (await _check(client, posting_id=elsewhere)).json()
    assert body["alerts"] == [] and [i["application_id"] for i in body["info"]] == [first]
    # une offre « possible » (doublons rangés par l'analyse) sur la même entreprise
    async with app.state.session_factory() as db:
        from app.db.models.postings import JobPosting

        row = await db.get(JobPosting, elsewhere)
        assert row is not None
        row.duplicates = [{"level": "possible", "posting_id": other, "score": 0.93}]
        await db.commit()
    body = (await _check(client, posting_id=elsewhere)).json()
    assert [(a["level"], a["application_id"]) for a in body["alerts"]] == [("possible", first)]
    assert body["info"] == []


async def test_check_by_url_before_analysis_is_certain_only(client: httpx.AsyncClient) -> None:
    first = await created_id(
        client, company="Société Fictive", title="Développeuse IA",
        url="https://jobs.example.org/offres/5",
    )  # fmt: skip
    await created_id(client, company="Autre SA", title="Poste", status="applied")
    r = await _check(client, url="https://www.jobs.example.org/offres/5/?utm_campaign=x")
    body = r.json()
    assert [(a["level"], a["application_id"]) for a in body["alerts"]] == [("certain", first)]
    assert body["own"] is None and body["info"] == []
    r = await _check(client, url="https://jobs.example.org/offres/6")
    assert r.json() == {"own": None, "alerts": [], "info": []}


async def test_check_needs_exactly_one_input(client: httpx.AsyncClient) -> None:
    for params in ({}, {"posting_id": "a", "url": "https://example.org/x"}):
        r = await _check(client, **params)
        assert (r.status_code, r.json()["error"]["details"]) == (
            422,
            {"fields": ["posting_id", "url"]},
        )
    r = await _check(client, url="ftp://example.org/secrete")
    assert r.json()["error"]["details"] == {"fields": ["url"]} and "secrete" not in r.text
    r = await _check(client, posting_id="inconnue")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")


async def test_check_is_not_swallowed_by_the_id_route(client: httpx.AsyncClient) -> None:
    assert (await create(client, company="A", title="B")).status_code == 201
    assert (await client.get(f"{API}/stats")).status_code == 200
    assert (
        await client.get(f"{API}/check", params={"url": "https://example.org/a"})
    ).status_code == 200
