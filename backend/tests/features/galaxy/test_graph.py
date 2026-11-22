"""La Galaxie compose les données vivantes, sans diffuser les fichiers du Cerveau."""

import httpx
from fastapi import FastAPI

from app.db.models.lessons import Lesson
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.brain.test_linked_notes import _note
from tests.features.brain.test_sync import API, CONFIGURED_PATH, SYNC, auth, configure
from tests.features.program.support import MONDAY, add_goal, sample_plan
from tests.support.direct import seed_program

GALAXY = f"{API}/galaxy"


async def test_empty_galaxy_has_no_fabricated_nodes(client: httpx.AsyncClient) -> None:
    result = await client.get(GALAXY)
    assert result.status_code == 200
    assert result.json() == {"nodes": [], "edges": [], "target_label": None}


async def _chapter_behind_a_more_recent_program(app: FastAPI) -> str:
    seed = await seed_program(app)
    async with app.state.session_factory() as db:
        program = await load(db, seed.user_id, seed.program_id)
        program.program.status = "validated"
        lesson = Lesson(
            user_id=seed.user_id,
            program_id=seed.program_id,
            module_id=seed.modules[0],
            title="Chapitre fictif",
            status="ready",
            markdown="Texte de cours fictif.",
        )
        db.add(lesson)
        await db.commit()
        lesson_id = lesson.id
    goal = await add_goal(app.state.session_factory, seed.user_id)
    newer = await AgentProgramStore(app.state.program).save_draft(
        seed.user_id,
        "s-galaxy-new",
        goal.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Programme plus récent sans chapitre",
    )
    assert newer.program_id != seed.program_id
    async with app.state.session_factory() as db:
        program = await load(db, seed.user_id, newer.program_id)
        program.program.status = "validated"
        await db.commit()
    return lesson_id


async def test_graph_links_live_notes_and_a_skill_to_a_published_chapter(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    skill = await client.post(f"{API}/skills", json={"name": "pandas", "domain": "Données"})
    skill_id = skill.json()["id"]
    lesson_id = await _chapter_behind_a_more_recent_program(app)
    folder, token = await configure(client)
    await _note(client, folder, token, "fiches/depart.md", "Départ", "Texte privé [[Arrivée]].")
    await _note(client, folder, token, "fiches/suite.md", "Arrivée")
    await app.state.memory.jobs.join()

    view = await client.get(GALAXY)
    assert view.status_code == 200 and view.headers["cache-control"] == "no-store"
    assert CONFIGURED_PATH not in view.text and "Texte privé" not in view.text
    nodes = {node["title"]: node for node in view.json()["nodes"]}
    assert nodes["pandas"]["id"] == f"skill:{skill_id}" and nodes["pandas"]["gap"] > 0
    assert nodes["pandas"]["action"] == {"kind": "lesson", "ref": lesson_id}
    link = {"source": nodes["Départ"]["id"], "target": nodes["Arrivée"]["id"], "kind": "reference"}
    assert link in view.json()["edges"]

    removed = await client.post(
        f"{SYNC}/{folder['id']}/remove",
        headers=auth(token),
        json={"path": "fiches/suite.md"},
    )
    assert removed.status_code == 204
    after = (await client.get(GALAXY)).json()
    assert "Arrivée" not in {node["title"] for node in after["nodes"]}
    assert link not in after["edges"]


async def test_training_action_carries_the_skill_id(client: httpx.AsyncClient) -> None:
    skill = await client.post(f"{API}/skills", json={"name": "Sujet fictif"})
    [node] = (await client.get(GALAXY)).json()["nodes"]
    assert node["action"] == {"kind": "training", "ref": skill.json()["id"]}
