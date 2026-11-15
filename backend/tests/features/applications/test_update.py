"""Retouche d'une fiche (SPEC 6.1, D139) : champs, contacts remplacés, statut refusé (422), 404 pour
la fiche d'une autre utilisatrice."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.conftest import API, create, created_id
from tests.sessions_support import act_as

SOCIETE = {"company": "Société Fictive", "title": "Développeuse IA"}


async def test_status_via_patch_is_422(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await client.patch(f"{API}/{application_id}", json={"status": "applied"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "validation_error")
    assert r.json()["error"]["details"] == {"fields": ["status"]}
    assert (await client.get(f"{API}/{application_id}")).json()["status"] == "to_apply"


async def test_patch_changes_sent_fields_only(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE, notes="À relire")
    r = await client.patch(
        f"{API}/{application_id}",
        json={
            "title": "Ingénieure IA",
            "channel": "linkedin",
            "letter": "Madame, Monsieur,",
            "next_action": "Préparer l'entretien",
            "next_action_on": "2026-11-20",
            "url": "https://jobs.example.org/offres/9",
        },
    )
    assert r.status_code == 200, r.text
    detail = r.json()
    assert (detail["title"], detail["company"], detail["notes"]) == (
        "Ingénieure IA",
        "Société Fictive",
        "À relire",
    )
    assert (detail["channel"], detail["next_action"], detail["next_action_on"]) == (
        "linkedin",
        "Préparer l'entretien",
        "2026-11-20",
    )
    assert detail["letter"] == "Madame, Monsieur," and detail["url"].endswith("/offres/9")
    r = await client.patch(f"{API}/{application_id}", json={"notes": None, "channel": None})
    assert (r.json()["notes"], r.json()["channel"]) == (None, None)
    assert r.json()["title"] == "Ingénieure IA"


async def test_patch_company_refreshes_duplicate_key(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, company="Autre SA", title="Développeuse IA")
    await client.patch(f"{API}/{application_id}", json={"company": "Société Fictive"})
    r = await create(client, **SOCIETE)
    assert r.status_code == 409  # la clé d'entreprise suit le nom


async def test_patch_replaces_contacts(client: httpx.AsyncClient) -> None:
    application_id = await created_id(
        client, **SOCIETE, contacts=[{"name": "Premier"}, {"name": "Deuxième"}]
    )
    r = await client.patch(f"{API}/{application_id}", json={"notes": "Rien d'autre"})
    assert [c["name"] for c in r.json()["contacts"]] == ["Premier", "Deuxième"]  # non fournis
    r = await client.patch(
        f"{API}/{application_id}",
        json={"contacts": [{"name": "Troisième", "role": "RH", "url": "https://example.org/t"}]},
    )
    assert [(c["name"], c["role"]) for c in r.json()["contacts"]] == [("Troisième", "RH")]
    r = await client.patch(f"{API}/{application_id}", json={"contacts": []})
    assert r.json()["contacts"] == []
    r = await client.patch(f"{API}/{application_id}", json={"contacts": [{"name": "x"}] * 11})
    assert r.json()["error"]["details"] == {"fields": ["contacts"]}


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"company": None}, "company"),
        ({"title": "  "}, "title"),
        ({"contacts": None}, "contacts"),
        ({"url": "pas un lien secret"}, "url"),
        ({"inconnu": 1}, "inconnu"),
    ],
)
async def test_patch_422_names_the_field(
    client: httpx.AsyncClient, body: dict[str, object], field: str
) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await client.patch(f"{API}/{application_id}", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": [field]}
    assert "secret" not in r.text


async def test_other_user_sees_nothing(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await created_id(client, **SOCIETE)
    act_as(app, "autre-utilisatrice")
    assert (await client.get(API)).json() == []
    for r in (
        await client.get(f"{API}/{application_id}"),
        await client.patch(f"{API}/{application_id}", json={"notes": "x"}),
        await client.post(f"{API}/{application_id}/events", json={"kind": "note", "text": "x"}),
    ):
        assert (r.status_code, r.json()["error"]["code"]) == (404, "application_not_found")
    stats = (await client.get(f"{API}/stats")).json()
    assert sum(stats["by_status"].values()) == 0
    # sa propre fiche ne rappelle pas celle de January : pas de doublon entre utilisatrices
    assert (await create(client, **SOCIETE)).status_code == 201
