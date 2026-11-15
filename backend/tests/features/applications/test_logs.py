"""Journaux des candidatures (SPEC 17.2) : identifiants, statuts et codes seulement. Jamais une
entreprise, un intitulé, un contact, une note ni un texte d'offre."""

import logging

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.conftest import API, add_posting, add_version, create

SECRETS = (
    "Entreprise Ultra Secrète",
    "Intitulé Ultra Secret",
    "Contact Ultra Secret",
    "Note ultra secrète",
    "Texte ultra secret de l'offre",
    "ultra-secret.example.org",
    "Phrase ultra secrète du fil",
)


async def test_application_data_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, app: FastAPI
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    created = await create(
        client,
        company=SECRETS[0],
        title=SECRETS[1],
        notes=SECRETS[3],
        url=f"https://{SECRETS[5]}/offre",
        contacts=[{"name": SECRETS[2], "url": f"https://{SECRETS[5]}/contact"}],
    )
    assert created.status_code == 201
    application_id = created.json()["application"]["id"]
    await create(client, company=SECRETS[0].lower(), title=SECRETS[1])  # doublon : 409
    await client.post(
        f"{API}/{application_id}/events", json={"kind": "status", "status": "applied"}
    )
    await client.post(f"{API}/{application_id}/events", json={"kind": "note", "text": SECRETS[6]})
    await client.patch(f"{API}/{application_id}", json={"notes": SECRETS[3], "title": SECRETS[1]})
    posting = await add_posting(
        app, company=SECRETS[0] + " 2", title=SECRETS[1] + " 2", text=SECRETS[4]
    )
    await add_version(app, posting)
    await client.get(API)  # adoption de la version
    await client.get(f"{API}/check", params={"posting_id": posting})
    await client.get(f"{API}/check", params={"url": f"https://{SECRETS[5]}/offre"})
    await client.get(f"{API}/stats")
    assert caplog.records
    for secret in SECRETS:
        assert secret not in caplog.text
        assert secret.lower() not in caplog.text.lower()
    assert application_id in caplog.text  # l'identifiant, lui, y est
