"""Relances suggérées (SPEC 6.2, D140) : synchronisation, brouillons, actions Fait, Reporter,
Ignorer, effets sur le statut de la fiche. Horloge figée au 15 novembre 2026."""

from datetime import date, timedelta
from typing import Any

import httpx
from fastapi import FastAPI

from app.db.models.applications import KitItem
from tests.features.applications.conftest import API, add_posting, created_id

TODAY = date(2026, 11, 15)
REMINDERS = "/api/v1/reminders"
SOCIETE = {"company": "Société Fictive", "title": "Développeuse IA"}


def ago(days: int) -> str:
    return str(TODAY - timedelta(days=days))


async def applied(client: httpx.AsyncClient, days: int, **fields: Any) -> str:
    return await created_id(client, **{**SOCIETE, **fields}, status="applied", applied_on=ago(days))


async def due(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    r = await client.get(REMINDERS)
    assert r.status_code == 200, r.text
    return list(r.json())


async def every(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    r = await client.get(REMINDERS, params={"due": "false"})
    assert r.status_code == 200, r.text
    return list(r.json())


async def act(client: httpx.AsyncClient, reminder_id: str, action: str) -> httpx.Response:
    return await client.patch(f"{REMINDERS}/{reminder_id}", json={"action": action})


async def test_seven_days_without_answer_shows_reminder_with_draft(
    client: httpx.AsyncClient,
) -> None:
    application_id = await applied(client, 7)
    [r] = await due(client)
    assert r["kind"] == "linkedin_7" and r["application_id"] == application_id
    assert "Développeuse IA" in r["draft"] and "Société Fictive" in r["draft"]
    assert r["linkedin_search_url"] and r["channel"] == "linkedin" and r["contact"] is None
    assert r["company"] == "Société Fictive" and r["title"] == "Développeuse IA"
    assert (r["due_on"], r["status"]) == (str(TODAY), "pending")
    assert "Soci%C3%A9t%C3%A9%20Fictive%20D%C3%A9veloppeuse%20IA" in r["linkedin_search_url"]


async def test_nothing_due_before_seven_days(client: httpx.AsyncClient) -> None:
    await applied(client, 6)
    assert await due(client) == []
    upcoming = await every(client)
    assert [r["kind"] for r in upcoming] == ["linkedin_7", "email_14", "close_21"]
    assert [r["due_on"] for r in upcoming] == ["2026-11-16", "2026-11-23", "2026-11-30"]


async def test_sync_is_idempotent(client: httpx.AsyncClient) -> None:
    await applied(client, 21)
    first = await due(client)
    second = await due(client)
    assert [r["kind"] for r in first] == ["linkedin_7", "email_14", "close_21"]
    assert [r["id"] for r in first] == [r["id"] for r in second]
    assert len(await every(client)) == 3


async def test_done_followup_sets_followed_up(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 7)
    [r] = await due(client)
    done = await act(client, r["id"], "done")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "done"
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["status"] == "followed_up" and detail["applied_on"] == ago(7)
    kinds = [(e["kind"], e["status_to"]) for e in detail["events"]]
    assert ("reminder", None) in kinds and ("status", "followed_up") in kinds
    assert await due(client) == []
    # une relance faite reste dans le fil ; les suivantes restent attendues (« Relancée »)
    assert [(x["kind"], x["status"]) for x in detail["reminders"]] == [
        ("linkedin_7", "done"),
        ("email_14", "pending"),
        ("close_21", "pending"),
    ]


async def test_done_does_not_change_status_outside_the_first_step(
    client: httpx.AsyncClient,
) -> None:
    application_id = await applied(client, 7)
    [r] = await due(client)
    await client.post(
        f"{API}/{application_id}/events", json={"kind": "status", "status": "followed_up"}
    )
    assert (await act(client, r["id"], "done")).status_code == 200
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["status"] == "followed_up"
    assert [e["status_to"] for e in detail["events"] if e["kind"] == "status"] == ["followed_up"]


async def test_close_21_done_sets_no_answer(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 21)
    close = next(r for r in await due(client) if r["kind"] == "close_21")
    assert close["channel"] == "none" and close["linkedin_search_url"] is None
    assert "Sans réponse" in close["draft"]
    assert (await act(client, close["id"], "done")).status_code == 200
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["status"] == "no_answer"
    # les relances d'attente restantes disparaissent, la faite reste
    assert [(x["kind"], x["status"]) for x in detail["reminders"]] == [("close_21", "done")]
    assert detail["due_reminders"] == 0


async def test_postpone_twice_adds_six_days(client: httpx.AsyncClient) -> None:
    await applied(client, 7)
    [r] = await due(client)
    once = (await act(client, r["id"], "postpone")).json()
    assert (once["due_on"], once["status"]) == ("2026-11-18", "pending")
    assert await due(client) == []
    twice = (await act(client, r["id"], "postpone")).json()
    assert twice["due_on"] == "2026-11-21" and twice["status"] == "pending"
    [first, *_] = await every(client)
    assert (first["id"], first["due_on"]) == (r["id"], "2026-11-21")  # la synchro ne le défait pas


async def test_postpone_an_overdue_reminder_counts_from_today(client: httpx.AsyncClient) -> None:
    await applied(client, 14)
    first = next(r for r in await due(client) if r["kind"] == "linkedin_7")
    assert first["due_on"] == "2026-11-08"
    moved = (await act(client, first["id"], "postpone")).json()
    assert moved["due_on"] == "2026-11-18"


async def test_ignore_closes_with_an_event(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 7)
    [r] = await due(client)
    ignored = await act(client, r["id"], "ignore")
    assert ignored.json()["status"] == "ignored"
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert detail["status"] == "applied"  # ignorer ne change pas le statut
    assert [e["kind"] for e in detail["events"]].count("reminder") == 1
    assert await due(client) == []


async def test_closed_reminder_is_409(client: httpx.AsyncClient) -> None:
    await applied(client, 7)
    [r] = await due(client)
    assert (await act(client, r["id"], "done")).status_code == 200
    again = await act(client, r["id"], "done")
    assert again.status_code == 409 and again.json()["error"]["code"] == "reminder_closed"
    assert (await act(client, r["id"], "postpone")).status_code == 409
    await applied(client, 7, company="Autre SA", title="Poste")
    [other] = [x for x in await due(client) if x["company"] == "Autre SA"]
    assert (await act(client, other["id"], "ignore")).status_code == 200
    assert (await act(client, other["id"], "done")).status_code == 409


async def test_unknown_reminder_and_action(client: httpx.AsyncClient) -> None:
    missing = await act(client, "nope", "done")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "reminder_not_found"
    await applied(client, 7)
    [r] = await due(client)
    bad = await act(client, r["id"], "explode")
    assert bad.status_code == 422 and "explode" not in bad.text


async def test_contact_replaces_search_link(client: httpx.AsyncClient) -> None:
    contacts = [
        {"name": "Paul Durand", "role": "Responsable ingénierie"},
        {"name": "Julie Martin", "role": "Recruteuse", "url": "https://www.linkedin.com/in/x"},
    ]
    await applied(client, 7, contacts=contacts)
    [r] = await due(client)
    assert r["contact"]["name"] == "Julie Martin"  # la recruteuse d'abord
    assert r["linkedin_search_url"] is None
    assert r["draft"].startswith("Bonjour Julie,")
    await applied(client, 7, company="Autre SA", title="Poste", contacts=contacts[:1])
    [other] = [x for x in await due(client) if x["company"] == "Autre SA"]
    assert other["contact"]["name"] == "Paul Durand"  # sinon le premier


async def test_english_posting_gives_english_draft(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting = await add_posting(app, company="Exemple Tech", title="AI Engineer", language="en")
    await created_id(client, posting_id=posting, status="applied", applied_on=ago(7))
    [r] = await due(client)
    assert r["draft"].startswith("Hello,") and "AI Engineer" in r["draft"]
    assert "Bonjour" not in r["draft"]
    french = await add_posting(app, company="Autre SA", title="Ingénieure")
    await created_id(client, posting_id=french, status="applied", applied_on=ago(7))
    texts = {x["company"]: x["draft"] for x in await due(client)}
    assert texts["Autre SA"].startswith("Bonjour,")


async def _kit(app: FastAPI, application_id: str, status: str, content: str) -> None:
    async with app.state.session_factory() as db:
        db.add(
            KitItem(
                user_id=app.state.local_user_id,
                application_id=application_id,
                kind="followups",
                status=status,
                content=content,
            )
        )
        await db.commit()


async def test_kit_followup_used_when_ready(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await applied(client, 14)
    await _kit(app, application_id, "ready", "Mail du kit à sept jours.\n---\nMail à quatorze.")
    drafts = {r["kind"]: r["draft"] for r in await due(client)}
    assert drafts["linkedin_7"] == "Mail du kit à sept jours."
    assert drafts["email_14"] == "Mail à quatorze."


async def test_kit_followup_to_check_is_not_used(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await applied(client, 14)
    await _kit(app, application_id, "to_check", "Texte à vérifier.\n---\nAutre texte.")
    drafts = {r["kind"]: r["draft"] for r in await due(client)}
    assert "Texte à vérifier" not in drafts["linkedin_7"]
    assert "Société Fictive" in drafts["linkedin_7"]
    assert "Autre texte" not in drafts["email_14"]


async def test_interview_gives_thanks_and_news(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 30)
    await client.post(
        f"{API}/{application_id}/events",
        json={"kind": "status", "status": "interview", "interview_on": ago(8)},
    )
    kinds = {r["kind"]: r for r in await due(client)}
    assert set(kinds) == {"thanks", "news_7"}  # l'attente est levée par l'entretien
    assert "7 novembre 2026" in kinds["thanks"]["draft"]
    assert kinds["thanks"]["channel"] == "email"


async def test_answer_removes_pending_reminders_at_once(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 7)
    await due(client)
    await client.post(
        f"{API}/{application_id}/events", json={"kind": "status", "status": "rejected"}
    )
    assert await due(client) == []
    assert await every(client) == []


async def test_due_reminders_are_counted(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 14)  # écrit : la fiche est créée avec ses relances
    assert (await client.get(f"{API}/stats")).json()["due_reminders"] == 2
    [item] = (await client.get(API)).json()
    assert item["id"] == application_id and item["due_reminders"] == 2
    await applied(client, 1, company="Autre SA", title="Poste")
    assert (await client.get(f"{API}/stats")).json()["due_reminders"] == 2


async def test_changed_dates_move_the_anchor(client: httpx.AsyncClient) -> None:
    application_id = await applied(client, 7)
    assert len(await due(client)) == 1
    await client.patch(f"{API}/{application_id}", json={"applied_on": ago(2)})
    assert await due(client) == []  # l'ancre a changé : la relance due a disparu
    assert [r["due_on"] for r in await every(client)][0] == "2026-11-20"
