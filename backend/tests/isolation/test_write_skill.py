import httpx
from fastapi import FastAPI

from tests.agents.graphs.web_support import Factory, add_users
from tests.sessions_support import act_as


async def test_skill_catalog_creation_isolated(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    other = "second-owner"
    await add_users(db_session_factory, other)
    body = {"name": "Analyse SQL", "domain": "Données", "synonyms": ["SQL analytique"]}
    url = "/api/v1/skills"
    created = await client.post(url, json=body)
    assert created.status_code == 201, created.text
    first = created.json()["id"]
    detail = (await client.get(f"{url}/{first}")).json()
    assert detail["level"] is None and detail["evidence"] == []
    assert (await client.post(url, json={**body, "name": "analyse sql"})).status_code == 409
    assert (await client.post(url, json={**body, "level": "prouve"})).status_code == 422
    act_as(app, other)
    assert (await client.get(f"{url}/{first}")).status_code == 404
    second = await client.post(url, json=body)
    assert second.status_code == 201 and second.json()["id"] != first
