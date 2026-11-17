"""Routeur `activity` : le fil d'activité de chaque personne ne montre que ses propres événements
(relevés du radar, écritures de la mémoire), jamais ceux d'une autre."""

import httpx
from fastapi import FastAPI

from tests.features.activity.support import API, OTHER, Env, add_run, add_user, add_write, hours
from tests.sessions_support import act_as


async def _rows(client: httpx.AsyncClient) -> set[str]:
    """Les lignes sources du fil : l'identifiant d'un événement est `<source>:<ligne>[:<état>]`."""
    r = await client.get(API, params={"limit": 50})
    assert r.status_code == 200, r.text
    return {item["id"].split(":")[1] for item in r.json()["items"]}


async def test_activity_of_another_account_is_invisible(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    env = Env(app, app.state.local_user_id)
    await add_user(env)
    mine = {await add_run(env, hours(1)), await add_write(env, hours(2), title="Mon écriture")}
    theirs = {
        await add_run(env, hours(3), user=OTHER),
        await add_write(env, hours(4), user=OTHER, title="Écriture de l'autre"),
    }
    assert await _rows(client) == mine
    assert "Écriture de l'autre" not in (await client.get(API)).text

    act_as(app, OTHER)
    assert await _rows(client) == theirs
    assert "Mon écriture" not in (await client.get(API)).text
