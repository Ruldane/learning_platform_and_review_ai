from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as


@pytest.fixture
async def watch_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=60),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def test_sources_and_updates_stay_private(
    app: FastAPI, watch_client: httpx.AsyncClient
) -> None:
    second_account = "autre-compte-veille"
    async with app.state.session_factory() as db:
        db.add(User(id=second_account, user_id=second_account))
        await db.commit()
    endpoint = "/api/v1/contradictory-watch"
    created = await watch_client.post(
        endpoint,
        json={
            "title": "Veille privée",
            "sources": [
                {"url": "https://example.org/test", "version": "1", "claim": "Premier avis"},
                {"url": "https://example.org/test", "version": "2", "claim": "Autre avis"},
            ],
            "protocol": "Mesurer sur les mêmes données.",
            "criterion": "Compter les lignes.",
        },
    )
    assert created.status_code == 201, created.text
    path = f"{endpoint}/{created.json()['id']}"
    act_as(app, second_account)
    assert (await watch_client.get(endpoint)).json() == []
    assert (await watch_client.get(path)).status_code == 404
    wrong = {"measurement": "autre compte", "outcome": "first"}
    assert (await watch_client.post(f"{path}/observations", json=wrong)).status_code == 404
