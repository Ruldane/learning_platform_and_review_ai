"""Contrats d'écriture de leçons et isolation des brouillons soumis."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.lessons import Lesson
from tests.agents.graphs.lesson_support import LessonModels
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, Seed, assert_no_agent
from tests.support.lesson_verification import submission_text, wait_session

pytestmark = pytest.mark.usefixtures("settled_indexing")
SECRET = "SECRET-DE-LA-LECON"


async def test_retry_reuses_the_pending_submission_and_existing_lesson_row(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, accept_lesson: LessonModels
) -> None:
    accept_lesson.block = lambda agent, _prompt: agent == "verifier"
    path = f"{API}/modules/{drafted.modules[1]}/lesson"
    title = "Module Projet"
    async with app.state.session_factory() as db:
        row = Lesson(
            user_id=drafted.user_id,
            module_id=drafted.modules[1],
            program_id=drafted.program_id,
            title=title,
            status="pending",
        )
        db.add(row)
        await db.commit()
        lesson_id = row.id

    body = {"markdown": submission_text(title)}
    first = await client.post(path, json=body)
    again = await client.post(path, json=body)
    other = await client.post(path, json={"markdown": submission_text(title, "nouvelle idée")})

    assert first.status_code == again.status_code == 202
    assert first.json() == again.json()
    lesson = first.json()
    assert lesson["status"] == "generating" and lesson["id"] == lesson_id
    assert (other.status_code, other.json()["error"]["code"]) == (409, "lesson_generating")
    async with app.state.session_factory() as db:
        assert list(await db.scalars(select(Lesson.id))) == [lesson_id]


async def test_patch_of_a_lesson_that_is_not_ready_is_refused(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed
) -> None:
    async with app.state.session_factory() as db:
        row = Lesson(
            user_id=drafted.user_id,
            module_id=drafted.modules[0],
            program_id=drafted.program_id,
            title="x",
            status="pending",
        )
        db.add(row)
        await db.commit()
        lesson_id = row.id

    response = await client.patch(f"{API}/lessons/{lesson_id}", json={"title": "Nouveau"})

    assert (response.status_code, response.json()["error"]["code"]) == (409, "lesson_not_ready")


async def test_invalid_input_is_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed
) -> None:
    url = f"{API}/modules/{drafted.modules[0]}/lesson"
    for body in (
        {"markdown": SECRET * 10_000},
        {"markdown": ""},
        {"markdown": SECRET, "title": SECRET * 40},
        {"title": SECRET},
    ):
        response = await client.post(url, json=body)
        assert response.status_code == 422, body
        assert SECRET not in response.text
    nothing = await client.patch(f"{API}/lessons/inconnue", json={})
    assert nothing.status_code == 422 and SECRET not in nothing.text
    await assert_no_agent(app)


@pytest.mark.usefixtures("accept_lesson")
@pytest.mark.usefixtures("accept_lesson")
async def test_lesson_write_is_isolated_between_users(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed
) -> None:
    made = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson",
        json={"markdown": submission_text("Module Bases")},
    )
    assert made.status_code == 202, made.text
    lesson_id = made.json()["id"]
    sid = made.json()["verification_session_id"]
    act_as(app, OTHER)

    other_write = await client.post(
        f"{API}/modules/{drafted.modules[1]}/lesson",
        json={"markdown": submission_text("Module Projet")},
    )
    other_patch = await client.patch(f"{API}/lessons/{lesson_id}", json={"title": "Pris"})

    assert (other_write.status_code, other_write.json()["error"]["code"]) == (
        404,
        "module_not_found",
    )
    assert (other_patch.status_code, other_patch.json()["error"]["code"]) == (
        404,
        "lesson_not_found",
    )
    assert (await client.get(f"{API}/sessions/{sid}")).status_code == 404
    act_as(app, drafted.user_id)
    assert (await wait_session(client, sid))["status"] == "completed"
    response = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson",
        json={"markdown": submission_text("Module Bases")},
    )
    assert (response.status_code, response.json()["error"]["code"]) == (409, "lesson_exists")
