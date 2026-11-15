"""Le fil d'une fiche (SPEC 6.1, D139) : changements de statut (dates de `on_status`, version
figée à « Postulée »), notes, dates données, 422 sans écho."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.conftest import API, add_posting, add_version, created_id

SOCIETE = {"company": "Société Fictive", "title": "Développeuse IA"}


async def _event(client: httpx.AsyncClient, application_id: str, **body: object) -> httpx.Response:
    return await client.post(f"{API}/{application_id}/events", json=body)


async def test_status_event_sets_dates_and_thread(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, kind="status", status="applied", text="Envoyée")
    assert r.status_code == 200, r.text
    detail = r.json()
    assert (detail["status"], detail["applied_on"]) == ("applied", "2026-11-15")
    last = detail["events"][-1]
    assert (last["kind"], last["status_from"], last["status_to"]) == (
        "status",
        "to_apply",
        "applied",
    )
    assert last["text"] == "Envoyée"
    r = await _event(client, application_id, kind="status", status="rejected", on="2026-11-20")
    detail = r.json()
    assert detail["status"] == "rejected" and detail["applied_on"] == "2026-11-15"
    stats = (await client.get(f"{API}/stats")).json()
    assert stats["by_status"]["rejected"] == 1 and stats["mean_response_days"] == 5.0
    assert stats["response_rate"] == 1.0


async def test_event_on_a_past_day_is_dated_then(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, kind="status", status="applied", on="2026-11-03")
    detail = r.json()
    assert detail["applied_on"] == "2026-11-03"
    [event] = [e for e in detail["events"] if e["kind"] == "status"]
    assert event["at"].startswith("2026-11-03T11:00:00")  # midi à Paris, en UTC
    assert [e["kind"] for e in detail["events"]] == ["status", "created"]  # fil chronologique


async def test_interview_day_defaults_to_the_event_day(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE, status="applied")
    r = await _event(client, application_id, kind="status", status="interview", on="2026-11-14")
    assert (r.json()["interview_on"], r.json()["status"]) == ("2026-11-14", "interview")
    other = await created_id(client, company="Autre SA", title="Poste", status="applied")
    r = await _event(client, other, kind="status", status="interview", interview_on="2026-11-25")
    assert r.json()["interview_on"] == "2026-11-25"


async def test_same_status_adds_nothing(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, kind="status", status="to_apply")
    assert [e["kind"] for e in r.json()["events"]] == ["created"]


async def test_note_event(client: httpx.AsyncClient) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, kind="note", text="Appel de la RH demain.")
    detail = r.json()
    assert detail["status"] == "to_apply"
    assert [(e["kind"], e["text"]) for e in detail["events"]] == [
        ("created", None),
        ("note", "Appel de la RH demain."),
    ]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"kind": "status"}, "status"),
        ({"kind": "note"}, "text"),
        ({"kind": "note", "text": "   "}, "text"),
        ({"kind": "status", "status": "gagné"}, "status"),
        ({"kind": "autre"}, "kind"),
    ],
)
async def test_event_422_names_the_field(
    client: httpx.AsyncClient, body: dict[str, str], field: str
) -> None:
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, **body)
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": [field]}
    assert "gagné" not in r.text


async def test_event_on_unknown_application_is_404(client: httpx.AsyncClient) -> None:
    r = await _event(client, "inconnue", kind="note", text="x")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "application_not_found")


async def test_applied_freezes_version(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    application_id = await created_id(client, posting_id=posting)
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["cv_version_id"] == ready_version and detail["cv_version_number"] == 1
    r = await _event(client, application_id, kind="status", status="applied")
    detail = r.json()
    assert detail["cv_version_id"] == ready_version
    versions = [e for e in detail["events"] if e["kind"] == "version"]
    assert [(e["ref_id"], e["text"]) for e in versions] == [
        (ready_version, "Version 1 du CV envoyée.")
    ]


async def test_version_frozen_after_applied(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    application_id = await created_id(client, posting_id=posting)
    await _event(client, application_id, kind="status", status="applied")
    await add_version(app, posting, number=2)
    listed = (await client.get(API)).json()  # l'adoption ne touche pas une fiche postulée
    assert [(a["id"], a["cv_version_id"], a["cv_version_number"]) for a in listed] == [
        (application_id, ready_version, 1)
    ]
    # revenir à « À postuler » ne rend pas la fiche suiveuse : la version envoyée reste
    await _event(client, application_id, kind="status", status="to_apply")
    again = (await client.get(f"{API}/{application_id}")).json()
    assert again["cv_version_id"] == ready_version
    # une fiche créée « Postulée » depuis l'offre fige aussi
    second = await add_posting(app, company="Exemple Tech", title="Autre poste")
    second_version = await add_version(app, second)
    other = await created_id(client, posting_id=second, status="applied")
    assert (await client.get(f"{API}/{other}")).json()["cv_version_id"] == second_version
