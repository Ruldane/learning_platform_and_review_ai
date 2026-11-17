"""Écriture directe d'une leçon (10.W) : `POST /modules/{id}/lesson` et `PATCH /lessons/{id}`
rangent le Markdown de January ou de Claude comme le port du Rédacteur, sans agent ni appel au
modèle."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.lessons import Lesson
from app.db.models.memory import MemoryItem
from app.features.memory.service.direct import drain_indexing
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, Seed, assert_no_agent, lesson_text

MARKDOWN = lesson_text("Une leçon écrite à la main, avec assez de mots pour compter.")
pytestmark = pytest.mark.usefixtures("settled_indexing")
SECRET = "SECRET-DE-LA-LECON"


async def memory_items(app: FastAPI, kind: str) -> list[MemoryItem]:
    async with app.state.session_factory() as db:
        stmt = select(MemoryItem).where(MemoryItem.kind == kind)
        return list((await db.execute(stmt)).scalars())


async def test_write_lesson_is_ready_without_any_agent(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    module = drafted.modules[0]
    r = await client.post(f"{API}/modules/{module}/lesson", json={"markdown": MARKDOWN})

    assert r.status_code == 201, r.text
    lesson = r.json()
    assert lesson["status"] == "ready" and lesson["markdown"] == MARKDOWN
    assert lesson["title"] == "Module Bases" and lesson["module_id"] == module
    assert lesson["word_count"] == len(MARKDOWN.split()) and lesson["pdf_available"] is False
    assert lesson["resources"] == [] and lesson["failure_reason"] is None
    assert (await client.get(f"{API}/lessons/{lesson['id']}")).json() == lesson
    listed = (await client.get(f"{API}/programs/{drafted.program_id}/lessons")).json()
    assert [row["id"] for row in listed] == [lesson["id"]]
    [item] = await memory_items(app, "lecon")  # sa copie en mémoire, écrite par January, indexée
    assert (item.title, item.text, item.created_by) == ("Module Bases", MARKDOWN.strip(), "user")
    await drain_indexing()  # l'indexation suit, hors de l'appel (voir tests/mcp/test_direct_memory)
    assert (await memory_items(app, "lecon"))[0].indexed_at is not None
    await assert_no_agent(app)


async def test_write_lesson_with_own_title_then_patch(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    made = await client.post(
        f"{API}/modules/{drafted.modules[1]}/lesson",
        json={"title": "Mon titre", "markdown": MARKDOWN},
    )
    assert made.status_code == 201 and made.json()["title"] == "Mon titre"
    lesson_id = made.json()["id"]

    patched = await client.patch(
        f"{API}/lessons/{lesson_id}", json={"markdown": MARKDOWN + "\nUn paragraphe de plus.\n"}
    )

    assert patched.status_code == 200, patched.text
    assert patched.json()["markdown"].endswith("Un paragraphe de plus.\n")
    assert patched.json()["word_count"] == len(patched.json()["markdown"].split())
    renamed = await client.patch(f"{API}/lessons/{lesson_id}", json={"title": "Autre titre"})
    assert renamed.json()["title"] == "Autre titre" and renamed.json()["markdown"].startswith(
        "# Une"
    )
    [item] = await memory_items(app, "lecon")  # mis à jour, pas dupliqué
    assert item.title == "Autre titre" and "Un paragraphe de plus." in item.text
    await drain_indexing()
    await assert_no_agent(app)


async def test_write_lesson_twice_is_refused_and_pending_lesson_is_filled(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    async with app.state.session_factory() as db:
        db.add(
            Lesson(
                user_id=drafted.user_id,
                module_id=drafted.modules[1],
                program_id=drafted.program_id,
                title="Module Projet",
                status="pending",
            )
        )
        await db.commit()
    first = await client.post(
        f"{API}/modules/{drafted.modules[1]}/lesson", json={"markdown": MARKDOWN}
    )
    assert first.status_code == 201 and first.json()["status"] == "ready"

    again = await client.post(
        f"{API}/modules/{drafted.modules[1]}/lesson", json={"markdown": MARKDOWN}
    )

    assert again.status_code == 409 and again.json()["error"]["code"] == "lesson_exists"
    async with app.state.session_factory() as db:
        rows = list((await db.execute(select(Lesson))).scalars())
    assert len(rows) == 1  # la leçon posée par la production a été remplie, pas doublée


async def test_patch_of_a_lesson_that_is_not_ready_is_refused(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
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

    r = await client.patch(f"{API}/lessons/{lesson_id}", json={"title": "Nouveau"})

    assert r.status_code == 409 and r.json()["error"]["code"] == "lesson_not_ready"


async def test_invalid_lesson_is_422_without_echo(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    url = f"{API}/modules/{drafted.modules[0]}/lesson"
    for body in (
        {"markdown": SECRET * 10_000},
        {"markdown": ""},
        {"markdown": SECRET, "title": SECRET * 40},
        {"title": SECRET},
    ):
        r = await client.post(url, json=body)
        assert r.status_code == 422, body
        assert SECRET not in r.text
    nothing = await client.patch(f"{API}/lessons/inconnue", json={})
    assert nothing.status_code == 422 and SECRET not in nothing.text


async def test_lesson_write_is_isolated_between_users(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    made = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson", json={"markdown": MARKDOWN}
    )
    lesson_id = made.json()["id"]
    act_as(app, OTHER)

    other_write = await client.post(
        f"{API}/modules/{drafted.modules[1]}/lesson", json={"markdown": MARKDOWN}
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
    act_as(app, drafted.user_id)
    assert (await client.get(f"{API}/lessons/{lesson_id}")).json()["title"] == "Module Bases"


async def test_a_lesson_needs_at_least_300_characters(
    client: httpx.AsyncClient, drafted: Seed
) -> None:
    url = f"{API}/modules/{drafted.modules[0]}/lesson"
    short = await client.post(url, json={"markdown": "x" * 299})
    assert short.status_code == 422 and "x" * 20 not in short.text
    made = await client.post(url, json={"markdown": "x" * 300})
    assert made.status_code == 201
    patched = await client.patch(f"{API}/lessons/{made.json()['id']}", json={"markdown": "x" * 299})
    assert patched.status_code == 422
    await drain_indexing()
