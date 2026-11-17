"""Routeur `settings` : les réglages de chaque compte sont les siens (valeurs par défaut pour qui
n'a rien changé), et ce que l'un écrit n'atteint jamais l'autre."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as

SETTINGS = "/api/v1/settings"
OTHER = "autre-utilisatrice"


async def test_settings_are_each_accounts_own(client: httpx.AsyncClient, app: FastAPI) -> None:
    mine = (await client.get(SETTINGS)).json() | {
        "style_guide": "Style de la première.",
        "debate_rounds": 5,
        "radar_role": "Poste de la première",
        "onboarding_done": True,
    }
    assert (await client.put(SETTINGS, json=mine)).status_code == 200

    async with app.state.session_factory() as db:
        db.add(User(id=OTHER, user_id=OTHER))
        await db.commit()
    act_as(app, OTHER)
    theirs = (await client.get(SETTINGS)).json()
    assert theirs["style_guide"] == "" and theirs["debate_rounds"] == 3  # ses propres valeurs
    assert theirs["radar_role"] == "" and theirs["onboarding_done"] is False
    assert "Poste de la première" not in str((await client.get(SETTINGS)).text)

    # Elle écrit les siennes : la première ne les voit pas.
    written = theirs | {"style_guide": "Style de l'autre.", "debate_rounds": 2}
    assert (await client.put(SETTINGS, json=written)).status_code == 200
    assert (await client.get(SETTINGS)).json()["style_guide"] == "Style de l'autre."

    app.dependency_overrides.clear()
    first = (await client.get(SETTINGS)).json()
    assert (first["style_guide"], first["debate_rounds"]) == ("Style de la première.", 5)
    assert first["radar_role"] == "Poste de la première" and first["onboarding_done"] is True
