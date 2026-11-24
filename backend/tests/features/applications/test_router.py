"""Routes des candidatures (D139) : liste (ordre, filtres), détail, indicateurs, accès sans
connexion."""

import httpx

from tests.features.applications.conftest import API, create, created_id


async def test_list_is_newest_first_and_filters(client: httpx.AsyncClient) -> None:
    first = await created_id(client, company="Société Fictive", title="Poste A")
    second = await created_id(client, company="Autre SA", title="Poste B", status="applied")
    third = await created_id(client, company="Exemple Tech", title="Poste C")
    listed = (await client.get(API)).json()
    assert [a["id"] for a in listed] == [third, second, first]
    assert set(listed[0]) >= {
        "id", "posting_id", "company", "title", "url", "channel", "status", "applied_on",
        "interview_on", "cv_version_id", "cv_version_number", "next_action", "next_action_on",
        "due_reminders", "created_at", "updated_at",
    }  # fmt: skip
    assert "events" not in listed[0] and "posting_text" not in listed[0]
    applied = (await client.get(API, params={"status": "applied"})).json()
    assert [a["id"] for a in applied] == [second]
    r = await client.get(API, params={"status": "inconnu"})
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["status"]}


async def test_list_by_posting(client: httpx.AsyncClient, posting: str) -> None:
    await created_id(client, company="Autre SA", title="Poste B")
    mine = await created_id(client, posting_id=posting)
    listed = (await client.get(API, params={"posting_id": posting})).json()
    assert [a["id"] for a in listed] == [mine]


async def test_detail_of_unknown_application_is_404(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{API}/inconnue")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "application_not_found")
    assert r.json()["error"]["message"] == "Application not found."


async def test_stats_route(client: httpx.AsyncClient) -> None:
    empty = (await client.get(f"{API}/stats")).json()
    assert empty["response_rate"] is None and empty["mean_response_days"] is None
    assert empty["due_reminders"] == 0 and len(empty["by_status"]) == 8
    assert set(empty["by_status"].values()) == {0}
    sent = await created_id(client, company="Société Fictive", title="A", status="applied",
                            applied_on="2026-11-03")  # fmt: skip
    await created_id(
        client, company="Autre SA", title="B", status="applied", applied_on="2026-11-05"
    )
    await created_id(client, company="Exemple Tech", title="C")
    await client.post(
        f"{API}/{sent}/events", json={"kind": "status", "status": "interview", "on": "2026-11-09"}
    )
    stats = (await client.get(f"{API}/stats")).json()
    assert stats["by_status"]["applied"] == 1 and stats["by_status"]["interview"] == 1
    assert stats["by_status"]["to_apply"] == 1
    assert stats["response_rate"] == 0.5 and stats["mean_response_days"] == 6.0
    # A (entretien le 9) : remerciement dû le 10 ; B (postulée le 5) : relance de 7 jours due le 12
    assert stats["due_reminders"] == 2


async def test_due_reminders_are_counted(client: httpx.AsyncClient) -> None:
    application_id = await created_id(
        client, company="Société Fictive", title="A", status="applied", applied_on="2026-11-08"
    )
    assert (await client.get(f"{API}/stats")).json()["due_reminders"] == 1
    [fiche] = (await client.get(API)).json()
    assert fiche["due_reminders"] == 1
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert [(r["kind"], r["status"], r["due_on"]) for r in detail["reminders"]] == [
        ("linkedin_7", "pending", "2026-11-15"),
        ("email_14", "pending", "2026-11-22"),
        ("close_21", "pending", "2026-11-29"),
    ]


async def test_routes_need_a_user(client_google_mode: httpx.AsyncClient) -> None:
    for path in ("", "/stats", "/check?url=https://example.org/a", "/x"):
        assert (await client_google_mode.get(f"{API}{path}")).status_code == 401
    assert (await create(client_google_mode, company="A", title="B")).status_code == 401
