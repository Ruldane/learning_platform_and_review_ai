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
    r = await _event(
        client, application_id, kind="status", status="applied", text="Envoyée", on="2026-11-10"
    )
    assert r.status_code == 200, r.text
    detail = r.json()
    assert (detail["status"], detail["applied_on"]) == ("applied", "2026-11-10")
    [last] = [e for e in detail["events"] if e["kind"] == "status"]
    assert (last["kind"], last["status_from"], last["status_to"]) == (
        "status",
        "to_apply",
        "applied",
    )
    assert last["text"] == "Envoyée"
    r = await _event(client, application_id, kind="status", status="rejected", on="2026-11-15")
    detail = r.json()
    assert detail["status"] == "rejected" and detail["applied_on"] == "2026-11-10"
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


async def test_version_frozen_when_leaving_to_apply_for_any_status_but_withdrawn(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """La version envoyée est celle du jour où January quitte « À postuler » (sauf « Retirée »)."""
    postings = [await add_posting(app, company=f"Exemple {n}", title=f"Poste {n}") for n in "ABC"]
    first = [await add_version(app, p) for p in postings]
    ids = [await created_id(client, posting_id=p) for p in postings]
    for application_id, new in zip(ids, ("interview", "withdrawn", "applied"), strict=True):
        r = await _event(client, application_id, kind="status", status=new)
        assert r.status_code == 200, r.text
    second = [await add_version(app, p, number=2) for p in postings]
    listed = {a["id"]: a for a in (await client.get(API)).json()}
    assert listed[ids[0]]["cv_version_id"] == first[0]  # « Entretien » : figée
    assert listed[ids[1]]["cv_version_id"] == first[1]  # « Retirée » : rien de figé, rien de suivi
    assert second[1] != first[1]
    assert listed[ids[2]]["cv_version_id"] == first[2]  # « Postulée » : figée
    thread = (await client.get(f"{API}/{ids[0]}")).json()["events"]
    assert [e["ref_id"] for e in thread if e["kind"] == "version"] == [first[0]]
    # une fiche créée directement à « Entretien » fige aussi la version prête du jour
    direct = await add_posting(app, company="Exemple D", title="Poste D")
    wanted = await add_version(app, direct)
    created = await created_id(client, posting_id=direct, status="interview")
    await add_version(app, direct, number=2)
    assert (await client.get(f"{API}/{created}")).json()["cv_version_id"] == wanted
    # ... mais pas une fiche créée « Retirée » : rien n'est figé
    gone = await add_posting(app, company="Exemple E", title="Poste E")
    await add_version(app, gone)
    kept = await created_id(client, posting_id=gone, status="withdrawn")
    assert (await client.get(f"{API}/{kept}")).json()["cv_version_id"] is None


async def test_version_not_refrozen_after_back_to_to_apply(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """Postulée (V1), retour à « À postuler », V2 prête, « Postulée » de nouveau : V1 reste
    la version envoyée ; la fiche ne suit plus les nouvelles versions."""
    posting = await add_posting(app)
    first = await add_version(app, posting)
    application_id = await created_id(client, posting_id=posting)
    await _event(client, application_id, kind="status", status="applied")
    await _event(client, application_id, kind="status", status="to_apply")
    await add_version(app, posting, number=2)
    assert (await client.get(API)).json()[0]["cv_version_id"] == first  # ne suit plus
    detail = (await _event(client, application_id, kind="status", status="applied")).json()
    assert detail["cv_version_id"] == first
    assert [e["ref_id"] for e in detail["events"] if e["kind"] == "version"] == [first]
    # sortie vers « Entretien » sans version prête : rien n'est figé, la fiche suit encore
    other = await add_posting(app, company="Autre SA", title="Poste")
    ref = await created_id(client, posting_id=other)
    await _event(client, ref, kind="status", status="interview")
    await _event(client, ref, kind="status", status="to_apply")
    later = await add_version(app, other)
    detail = (await _event(client, ref, kind="status", status="applied")).json()
    assert detail["cv_version_id"] == later


async def test_event_in_future_is_422(client: httpx.AsyncClient) -> None:
    """M8 : un événement ne se date pas dans le futur (le jour de January, comme le formulaire) ;
    422 qui nomme `on`, sans écho ; aujourd'hui et hier passent."""
    application_id = await created_id(client, **SOCIETE)
    r = await _event(client, application_id, kind="note", text="x", on="2099-01-01")
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["on"]
    assert "2099" not in r.text
    r = await _event(client, application_id, kind="status", status="applied", on="2026-11-16")
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == ["on"]
    assert (
        await _event(client, application_id, kind="note", text="x", on="2026-11-15")
    ).status_code == 200
    assert (
        await _event(client, application_id, kind="note", text="y", on="2026-11-14")
    ).status_code == 200
