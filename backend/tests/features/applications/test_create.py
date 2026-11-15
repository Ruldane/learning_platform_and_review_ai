"""Création d'une fiche (SPEC 6.1 n° 2, 6.3, D139) : à la main, depuis une offre (texte et lien
figés), doublons (409 avec les fiches existantes, jamais l'entrée), « autre poste » dans les deux
sens, information « même entreprise », 422 sans écho."""

import httpx
from fastapi import FastAPI

from tests.features.applications.conftest import (
    API,
    add_posting,
    create,
    created_id,
)

SOCIETE = {"company": "Société Fictive", "title": "Développeuse IA"}


async def test_manual_create_then_detail(client: httpx.AsyncClient) -> None:
    r = await create(
        client,
        **SOCIETE,
        url="https://jobs.example.org/offres/1?utm_source=news",
        channel="job_board",
        notes="Offre vue sur un site.",
        contacts=[
            {"name": "Camille Exemple", "role": "Recruteuse", "url": "https://example.org/c"}
        ],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["info"] == []
    created = body["application"]
    assert (created["status"], created["company"], created["channel"]) == (
        "to_apply",
        "Société Fictive",
        "job_board",
    )
    assert [e["kind"] for e in created["events"]] == ["created"]
    assert created["events"][0]["status_to"] == "to_apply"
    assert [(c["name"], c["role"]) for c in created["contacts"]] == [
        ("Camille Exemple", "Recruteuse")
    ]
    assert created["reminders"] == [] and created["due_reminders"] == 0
    assert created["created_at"] and created["cv_version_id"] is None
    detail = (await client.get(f"{API}/{created['id']}")).json()
    assert detail == created


async def test_create_from_posting_freezes_text(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting_id = await add_posting(
        app, text="Texte figé de l'offre fictive.", url="https://jobs.example.org/offres/42"
    )
    r = await create(client, posting_id=posting_id)
    assert r.status_code == 201, r.text
    created = r.json()["application"]
    assert created["posting_id"] == posting_id
    assert created["posting_text"] == "Texte figé de l'offre fictive."
    assert created["url"] == "https://jobs.example.org/offres/42"
    assert (created["company"], created["title"]) == ("Société Fictive", "Développeuse IA")
    again = await create(client, posting_id=posting_id)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "application_exists")
    assert again.json()["error"]["details"] == {"application_id": created["id"]}


async def test_unknown_posting_is_404(client: httpx.AsyncClient) -> None:
    r = await create(client, posting_id="inconnue")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")


async def test_manual_create_duplicate_is_409_with_existing(client: httpx.AsyncClient) -> None:
    await create(client, **SOCIETE, status="applied", applied_on="2026-11-03")
    r = await create(client, company="société fictive", title="Développeuse IA (H/F)")
    assert r.status_code == 409 and r.json()["error"]["code"] == "application_duplicate"
    assert r.json()["error"]["message"] == "Cette offre ressemble à une candidature existante."
    alert = r.json()["error"]["details"]["alerts"][0]
    assert alert["level"] == "probable" and "le 3 novembre" in alert["message"]
    assert "Postulée" in alert["message"]
    assert (alert["company"], alert["title"]) == ("Société Fictive", "Développeuse IA")
    assert "H/F" not in r.text  # l'entrée n'est jamais renvoyée
    assert len((await client.get(API)).json()) == 1


async def test_same_link_is_certain_whatever_the_tracking(client: httpx.AsyncClient) -> None:
    await create(client, **SOCIETE, url="https://jobs.example.org/offres/7")
    r = await create(
        client,
        company="Autre SA",
        title="Autre poste",
        url="https://www.jobs.example.org/offres/7/?utm_source=mail",
    )
    assert r.status_code == 409
    assert r.json()["error"]["details"]["alerts"][0]["level"] == "certain"


async def test_distinct_confirmation_silences_pair(client: httpx.AsyncClient, app: FastAPI) -> None:
    first = await created_id(client, **SOCIETE, status="applied", applied_on="2026-11-03")
    posting_id = await add_posting(app, title="Développeuse IA (H/F)")
    refused = await create(client, posting_id=posting_id)
    assert refused.status_code == 409
    [alert] = refused.json()["error"]["details"]["alerts"]
    assert alert["application_id"] == first
    r = await create(client, posting_id=posting_id, distinct_from=[first])
    assert r.status_code == 201, r.text
    assert r.json()["info"] == []
    second = r.json()["application"]["id"]
    check = (await client.get(f"{API}/check", params={"posting_id": posting_id})).json()
    assert check["alerts"] == [] and check["own"]["id"] == second  # plus d'alerte ensuite


async def test_same_company_info_is_201_with_info(client: httpx.AsyncClient) -> None:
    first = await created_id(client, company="Société Fictive", title="Responsable Marketing")
    r = await create(client, **SOCIETE)
    assert r.status_code == 201, r.text
    [info] = r.json()["info"]
    assert (info["level"], info["application_id"]) == ("info", first)
    assert info["message"].startswith("Pour info")


async def test_applied_creation_sets_the_date(client: httpx.AsyncClient) -> None:
    r = await create(client, **SOCIETE, status="applied")
    assert r.json()["application"]["applied_on"] == "2026-11-15"
    r = await create(
        client, company="Autre SA", title="Poste", status="applied", applied_on="2026-11-03"
    )
    assert r.json()["application"]["applied_on"] == "2026-11-03"


async def test_manual_needs_company_and_title(client: httpx.AsyncClient) -> None:
    r = await create(client, company="Société Fictive")
    assert (r.status_code, r.json()["error"]["code"]) == (422, "validation_error")
    assert r.json()["error"]["details"] == {"fields": ["title"]}
    r = await create(client, notes="rien")
    assert r.json()["error"]["details"] == {"fields": ["company", "title"]}


async def test_422_never_echoes_input(client: httpx.AsyncClient) -> None:
    long_name = "Entreprise-secrète-" + "x" * 500
    r = await create(client, company=long_name, title="Poste secret", notes="Note privée")
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["company"]}
    assert "secrète" not in r.text and "Poste secret" not in r.text and "privée" not in r.text
    r = await create(client, **SOCIETE, url="ftp://example.org/offre-secrete")
    assert r.json()["error"]["details"] == {"fields": ["url"]}
    assert "secrete" not in r.text
    r = await create(client, **SOCIETE, contacts=[{"name": "Nom"}] * 11)
    assert r.json()["error"]["details"] == {"fields": ["contacts"]}
    r = await create(client, **SOCIETE, status="inconnu")
    assert r.json()["error"]["details"] == {"fields": ["status"]}


async def test_unanalysed_posting_with_typed_fields_is_checked_like_a_manual_one(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """L'offre n'est pas analysée (ni entreprise ni intitulé rangés) : le contrôle lit ce que
    January a saisi, comme pour une fiche manuelle identique (409, et `info` pour un autre
    intitulé de la même entreprise)."""
    first = await created_id(client, **SOCIETE, status="applied", applied_on="2026-11-03")
    fresh = await add_posting(app, analyzed=False)
    r = await create(client, posting_id=fresh, **SOCIETE)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "application_duplicate")
    assert [a["application_id"] for a in r.json()["error"]["details"]["alerts"]] == [first]
    other = await add_posting(app, analyzed=False)
    r = await create(client, posting_id=other, company="Société Fictive", title="Comptable")
    assert r.status_code == 201, r.text
    assert [(i["level"], i["application_id"]) for i in r.json()["info"]] == [("info", first)]
    assert r.json()["application"]["posting_id"] == other


async def test_distinct_confirmation_silences_pair_in_the_reverse_direction(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """A née d'une offre PA ; B manuelle, confirmée « autre poste » de A : le contrôle de PA ne
    rappelle pas B, et une fiche identique à B qui ne confirme que A est acceptée."""
    posting_a = await add_posting(app, title="Développeuse IA")
    fiche_a = await created_id(client, posting_id=posting_a)
    refused = await create(client, company="Société Fictive", title="Développeuse IA (H/F)")
    assert refused.status_code == 409
    fiche_b = await created_id(
        client, company="Société Fictive", title="Développeuse IA (H/F)", distinct_from=[fiche_a]
    )
    check = (await client.get(f"{API}/check", params={"posting_id": posting_a})).json()
    assert check["alerts"] == [] and check["own"]["id"] == fiche_a
    again = await create(
        client, company="Société Fictive", title="Développeuse IA (H/F)", distinct_from=[fiche_a]
    )
    assert again.status_code == 409  # B ne l'est pas : seule A est confirmée
    assert [a["application_id"] for a in again.json()["error"]["details"]["alerts"]] == [fiche_b]
    both = await create(
        client,
        company="Société Fictive",
        title="Développeuse IA (H/F)",
        distinct_from=[fiche_a, fiche_b],
    )
    assert both.status_code == 201


async def test_other_user_posting_is_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    theirs = await add_posting(app, user_id="autre-utilisatrice")
    r = await create(client, posting_id=theirs)
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")
