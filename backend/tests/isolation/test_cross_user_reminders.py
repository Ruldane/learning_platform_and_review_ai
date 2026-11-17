"""Routeur `reminders` : les relances d'une personne sont invisibles pour une autre (liste vide,
404 sur l'identifiant), et agir dessus est impossible."""

from datetime import date, timedelta

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as

API = "/api/v1"
OTHER = "autre-utilisatrice"


async def test_reminders_of_another_account_are_invisible(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    created = await client.post(
        f"{API}/applications",
        json={
            "company": "Société Fictive",
            "title": "Développeuse IA",
            "status": "applied",
            "applied_on": str(date.today() - timedelta(days=50)),
        },
    )
    assert created.status_code == 201, created.text
    mine = (await client.get(f"{API}/reminders", params={"due": "false"})).json()
    assert len(mine) == 3  # relance à 7, 14 et 21 jours

    async with app.state.session_factory() as db:
        db.add(User(id=OTHER, user_id=OTHER))
        await db.commit()
    act_as(app, OTHER)
    for due in ("true", "false"):
        assert (await client.get(f"{API}/reminders", params={"due": due})).json() == []
    for action in ("done", "postpone", "ignore"):
        r = await client.patch(f"{API}/reminders/{mine[0]['id']}", json={"action": action})
        assert (r.status_code, r.json()["error"]["code"]) == (404, "reminder_not_found")

    app.dependency_overrides.clear()
    after = (await client.get(f"{API}/reminders", params={"due": "false"})).json()
    assert [(r["id"], r["status"]) for r in after] == [(r["id"], "pending") for r in mine]
