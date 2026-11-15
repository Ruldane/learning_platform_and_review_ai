"""Journaux des relances (SPEC 17.2) : identifiants et codes seulement, jamais un brouillon, un
nom de contact, une entreprise, un intitulé ni le lien de recherche."""

import logging
from datetime import date, timedelta

import httpx
import pytest

from tests.features.applications.conftest import created_id

SECRETS = (
    "Entreprise Ultra Secrète",
    "Intitulé Ultra Secret",
    "Contact Ultra Secret",
    "Ultra%20Secr",
)


async def test_reminder_data_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    day = str(date(2026, 11, 15) - timedelta(days=21))
    for contacts in ([], [{"name": SECRETS[2], "role": "Recruteur"}]):
        await created_id(
            client, company=SECRETS[0], title=SECRETS[1] if not contacts else "Zzz Ultra Secret",
            status="applied", applied_on=day, contacts=contacts,
        )  # fmt: skip
    listed = (await client.get("/api/v1/reminders")).json()
    assert len(listed) == 6 and all(SECRETS[1] in r["draft"] for r in listed[:1])
    ids = [r["id"] for r in listed]
    await client.patch(f"/api/v1/reminders/{ids[0]}", json={"action": "done"})
    await client.patch(f"/api/v1/reminders/{ids[1]}", json={"action": "postpone"})
    await client.patch(f"/api/v1/reminders/{ids[2]}", json={"action": "ignore"})
    await client.get("/api/v1/reminders", params={"due": "false"})
    assert caplog.records
    for secret in SECRETS:
        assert secret not in caplog.text
        assert secret.lower() not in caplog.text.lower()
    assert "linkedin.com/search" not in caplog.text
