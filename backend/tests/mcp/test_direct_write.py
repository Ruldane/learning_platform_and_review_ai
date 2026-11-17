"""Écriture directe par le MCP, sans agent (10.W) : chaque outil est de niveau 2, sans lancement de
graphe ; un appel écrit la ligne, le journal et l'historique la gardent, l'annulation la retire (y
compris l'élément de mémoire écrit avec la leçon ou l'offre) ; un jeton en lecture seule est
refusé."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.daily import Project
from app.db.models.ide import IdeExercise
from app.db.models.lessons import Lesson
from app.db.models.mcp import McpCall, McpChange
from app.db.models.memory import MemoryItem
from app.db.models.postings import JobPosting
from app.db.models.program import Module, Week
from app.db.models.study import Quiz, QuizQuestion
from scripts.sample_posting import POSTING_TEXT
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.direct import Seed, assert_no_agent
from tests.support.gap import analysis_data

FEATURES = ("lessons", "program", "projects", "postings", "quiz", "ide")
TOOLS = {
    "lessons_write_lesson",
    "lessons_update_lesson",
    "program_add_week",
    "program_update_week",
    "program_add_module",
    "program_update_module",
    "projects_write_project",
    "projects_update_project",
    "postings_write_posting",
    "postings_update_posting",
    "quiz_write_quiz",
    "quiz_update_quiz",
    "quiz_add_question",
    "quiz_update_question",
    "ide_update_exercise",
}
BRIEF = {
    "title": "Un pipeline de données",
    "context": "Tu reçois des fichiers CSV de ventes à nettoyer.",
    "objective": "Écrire un pipeline qui produit un fichier propre.",
    "constraints": ["Python seulement", "Pas de service externe"],
    "criteria": ["Le script tourne", "Les doublons sont retirés", "Un test existe"],
    "hours": 4,
    "deliverable": "repo",
}
QUESTION = {
    "type": "qcm",
    "prompt": "Que renvoie len([1, 2, 3]) ?",
    "choices": ["2", "3", "4"],
    "correct_index": 1,
    "skill": "pandas",
}


async def count(app: FastAPI, model: type[Any], **where: Any) -> int:
    async with app.state.session_factory() as db:
        stmt = select(model)
        for name, value in where.items():
            stmt = stmt.where(getattr(model, name) == value)
        return len((await db.execute(stmt)).scalars().all())


async def writer(claude: Mcp) -> str:
    return await claude.token(FEATURES, "write")


async def undo_last(claude: Mcp) -> httpx.Response:
    """Annule le dernier appel qui change quelque chose et n'est pas déjà annulé."""
    changes = (await claude.http.get(f"{API}/mcp/changes")).json()
    last = next(change for change in changes if change["undone_at"] is None)
    return await claude.http.post(f"{API}/mcp/changes/{last['call_id']}/undo")


async def test_every_direct_write_tool_is_level_2_without_graph(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    registry = app.state.mcp_registry
    for name in TOOLS:
        tool = registry.get(name)
        assert tool is not None, name
        assert (tool.level, tool.graph, tool.side_effects) == (2, None, "db"), name
        assert tool.description.count("Écriture directe, aucun agent") == 1, name


async def test_read_only_token_cannot_write(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await claude.token(FEATURES, "read")

    response = await claude.call(
        token, "lessons_write_lesson", {"module_id": drafted.modules[0], "markdown": "x"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "write_not_allowed"
    assert await count(app, Lesson) == 0


async def test_lesson_write_is_journaled_and_undone_with_its_memory_item(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await writer(claude)

    envelope, is_error = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": "# Leçon\n\nUn texte écrit par Claude.\n"},
    )

    assert not is_error, envelope
    lesson_id = envelope["data"]["id"]
    assert envelope["data"]["status"] == "ready"
    async with app.state.session_factory() as db:
        [item] = (await db.execute(select(MemoryItem).where(MemoryItem.kind == "lecon"))).scalars()
        journal = (await db.execute(select(McpCall))).scalars().all()
        recorded = {c.table_name for c in (await db.execute(select(McpChange))).scalars()}
    assert item.created_by == "claude" and item.indexed_at is not None
    assert [(c.action, c.level, c.code) for c in journal if c.action == "lessons_write_lesson"] == [
        ("lessons_write_lesson", 2, 201)
    ]
    assert {"lessons", "memory_items"} <= recorded
    await assert_no_agent(app)

    undone = await undo_last(claude)

    assert undone.status_code == 200, undone.text
    assert (await client.get(f"{API}/lessons/{lesson_id}")).status_code == 404
    assert await count(app, MemoryItem, kind="lecon") == 0


async def test_lesson_patch_is_undone_to_the_previous_text(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await writer(claude)
    made, _ = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": "Avant."},
    )
    lesson_id = made["data"]["id"]

    patched, is_error = await call(
        claude, token, "lessons_update_lesson", {"lesson_id": lesson_id, "markdown": "Après."}
    )
    assert not is_error and patched["data"]["markdown"] == "Après."
    assert (await undo_last(claude)).status_code == 200

    assert (await client.get(f"{API}/lessons/{lesson_id}")).json()["markdown"] == "Avant."
    async with app.state.session_factory() as db:
        [item] = (await db.execute(select(MemoryItem).where(MemoryItem.kind == "lecon"))).scalars()
    assert item.text == "Avant."  # l'élément de mémoire est celui d'avant la retouche


async def write_chain(claude: Mcp, token: str, drafted: Seed) -> list[dict[str, Any]]:
    """Une semaine, un module dedans, son quiz et son projet, par quatre appels du MCP."""
    week, e1 = await call(
        claude,
        token,
        "program_add_week",
        {
            "program_id": drafted.program_id,
            "theme": "Évaluation",
            "objective": "Mesurer.",
            "deliverable": "Un rapport",
        },
    )
    module, e2 = await call(
        claude,
        token,
        "program_add_module",
        {
            "program_id": drafted.program_id,
            "week_id": week["data"]["id"],
            "title": "Métriques",
            "skills": ["Évaluation"],
        },
    )
    module_id = module["data"]["id"]
    quiz, e3 = await call(
        claude,
        token,
        "quiz_write_quiz",
        {"module_id": module_id, "title": "Quiz métriques", "questions": [QUESTION]},
    )
    project, e4 = await call(
        claude, token, "projects_write_project", {"module_id": module_id, "brief": BRIEF}
    )
    assert not (e1 or e2 or e3 or e4), (week, module, quiz, project)
    return [week, module, quiz, project]


async def test_program_structure_and_quiz_and_project_writes_undo(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    await write_chain(claude, await writer(claude), drafted)
    assert (await count(app, Week), await count(app, Module)) == (3, 3)
    assert (await count(app, Quiz), await count(app, QuizQuestion), await count(app, Project)) == (
        1,
        1,
        1,
    )

    assert (await undo_last(claude)).status_code == 200  # le projet
    assert await count(app, Project) == 0
    assert (await undo_last(claude)).status_code == 200  # le quiz et ses questions
    assert (await count(app, Quiz), await count(app, QuizQuestion)) == (0, 0)
    assert (await undo_last(claude)).status_code == 200  # le module
    assert (await undo_last(claude)).status_code == 200  # la semaine
    assert (await count(app, Week), await count(app, Module)) == (2, 2)
    await assert_no_agent(app)


async def test_exercise_patch_is_undone(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await writer(claude)
    created = await client.post(
        f"{API}/ide/exercises", json={"title": "Boucles", "statement": "Avant."}
    )
    exercise_id = created.json()["id"]

    patched, is_error = await call(
        claude, token, "ide_update_exercise", {"exercise_id": exercise_id, "statement": "Après."}
    )
    assert not is_error and patched["data"]["statement"] == "Après."
    assert (await undo_last(claude)).status_code == 200

    async with app.state.session_factory() as db:
        row = await db.get(IdeExercise, exercise_id)
    assert row is not None and row.statement == "Avant."


async def test_posting_write_is_undone_with_its_memory_item_and_duplicates(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await writer(claude)
    analysis = analysis_data()
    analysis.pop("is_job_posting")
    first, e1 = await call(
        claude, token, "postings_write_posting", {**analysis, "text": POSTING_TEXT}
    )
    second, e2 = await call(
        claude,
        token,
        "postings_write_posting",
        {**analysis, "text": POSTING_TEXT + "\nAutre date de publication."},
    )
    assert not (e1 or e2), (first, second)
    first_id = first["data"]["posting"]["id"]
    levels = [d["level"] for d in second["data"]["posting"]["duplicates"]]
    assert levels == [
        "<donnee_non_fiable>probable</donnee_non_fiable>"
    ]  # texte venu du web : enclos
    assert await count(app, JobPosting) == 2 and await count(app, MemoryItem, kind="offre") == 2

    undone = await undo_last(claude)  # la seconde offre : le doublon réciproque disparaît aussi

    assert undone.status_code == 200, undone.text
    assert await count(app, JobPosting) == 1 and await count(app, MemoryItem, kind="offre") == 1
    kept = (await client.get(f"{API}/postings/{first_id}")).json()
    assert kept["duplicates"] == []
    await assert_no_agent(app)
