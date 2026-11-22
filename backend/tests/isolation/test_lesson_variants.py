from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.lessons import Lesson
from tests.features.lesson_variants.support import (
    EXAMPLE,
    OBJECTIVE,
    REFERENCE,
    SOURCE,
    seed_lesson,
)
from tests.sessions_support import act_as

API = "/api/v1/lesson-variants"


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=30),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as http,
    ):
        yield http


async def test_keeps_formats_on_the_original_revision(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson_id = await seed_lesson(app)
    body = {"lesson_id": lesson_id}
    response = await client.post(API, json=body)
    assert response.status_code == 201, response.text
    original = response.json()
    assert original["source_markdown"] == SOURCE
    assert original["revision"] and original["lesson_id"] == lesson_id
    assert original["reading_steps"] == [
        "Objectifs",
        "L’essentiel",
        "Explication",
        "Exemple travaillé",
        "Sources",
    ]
    review = original["review_markdown"]
    assert review != SOURCE
    assert review.index(EXAMPLE) < review.index("## Explication")
    for value in (OBJECTIVE, EXAMPLE, REFERENCE, "[doc]: https://example.org/index"):
        assert value in review
    assert (await client.post(API, json=body)).json()["id"] == original["id"]

    async with app.state.session_factory() as db:
        lesson = await db.get(Lesson, lesson_id)
        assert lesson is not None
        lesson.markdown = SOURCE + "\nNouvelle édition.\n"
        await db.commit()
    updated = (await client.post(API, json=body)).json()
    assert updated["revision"] != original["revision"]
    assert updated["id"] != original["id"]
    assert (await client.get(f"{API}/{original['id']}")).json() == original
    assert len((await client.get(API)).json()) == 2


async def test_requires_a_published_lesson_and_isolates_editions(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    unpublished = await seed_lesson(app, ready=False)
    response = await client.post(API, json={"lesson_id": unpublished})
    assert response.status_code == 409
    lesson_id = await seed_lesson(app)
    created = await client.post(API, json={"lesson_id": lesson_id})
    assert created.status_code == 201
    async with app.state.session_factory() as db:
        db.add(User(id="compte-variantes", user_id="compte-variantes"))
        await db.commit()
    act_as(app, "compte-variantes")
    assert (await client.post(API, json={"lesson_id": lesson_id})).status_code == 404
    assert (await client.get(f"{API}/{created.json()['id']}")).status_code == 404
    assert (await client.get(API)).json() == []
