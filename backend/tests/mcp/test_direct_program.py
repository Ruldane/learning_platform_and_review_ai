"""Objectif et programme complets écrits en direct par le MCP (D213) : deux outils de niveau 2 sans
agent, journalisés, annulables (l'annulation retire l'objectif ou le programme avec ses semaines,
modules et tâches) ; le programme se remplit ensuite avec les outils de 10.W, et sa validation reste
un geste de January (niveau 3)."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.learning import Goal
from app.db.models.mcp import McpCall
from app.db.models.program import Module, PlanVersion, Program, Task, Week
from tests.features.program.test_program_direct import START, program_body
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.mcp.test_direct_write import QUESTION, count, undo_last
from tests.support.direct import assert_no_agent, lesson_text

pytestmark = pytest.mark.usefixtures("settled_indexing")  # la leçon écrite est indexée après
FEATURES = ("learning", "program", "lessons", "quiz")
GOAL = {"text": "Les bases du ML pour l'ingénierie IA", "weekly_hours": 7, "target_role": "AI"}
TABLES = (Goal, Program, Week, Module, Task, PlanVersion)


async def sizes(app: FastAPI) -> tuple[int, ...]:
    return tuple([await count(app, model) for model in TABLES])


async def test_both_tools_are_level_2_without_graph(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    registry = app.state.mcp_registry
    for name in ("learning_write_goal", "program_write_program"):
        tool = registry.get(name)
        assert tool is not None, name
        assert (tool.level, tool.graph, tool.launches, tool.side_effects) == (
            2,
            None,
            None,
            "db",
        ), name
        assert tool.description.count("Écriture directe, aucun agent") == 1, name
    assert registry.get("learning_create_goal").launches == "learning_council"  # l'autre : un agent


async def test_goal_then_program_by_the_mcp_are_journaled_and_undone(
    client: httpx.AsyncClient, app: FastAPI, claude: Mcp
) -> None:
    token = await claude.token(FEATURES, "write")

    goal, e1 = await call(claude, token, "learning_write_goal", GOAL)
    assert not e1, goal
    goal_id = goal["data"]["id"]
    program, e2 = await call(
        claude, token, "program_write_program", program_body(goal_id, start_date=START.isoformat())
    )
    assert not e2, program

    data = program["data"]
    assert (data["status"], data["goal_id"], len(data["weeks"])) == ("draft", goal_id, 2)
    assert await sizes(app) == (1, 1, 2, 2, 12, 1)
    async with app.state.session_factory() as db:
        journal = (await db.execute(select(McpCall))).scalars().all()
    assert [(c.action, c.level, c.code) for c in journal if "write" in c.action] == [
        ("learning_write_goal", 2, 201),
        ("program_write_program", 2, 201),
    ]
    await assert_no_agent(app)

    assert (await undo_last(claude)).status_code == 200  # le programme et tout ce qu'il contient
    assert await sizes(app) == (1, 0, 0, 0, 0, 0)
    assert (await client.get(f"{API}/goals/{goal_id}")).json()["program_id"] is None
    assert (await undo_last(claude)).status_code == 200  # puis l'objectif
    assert await sizes(app) == (0, 0, 0, 0, 0, 0)
    await assert_no_agent(app)


async def test_a_program_written_by_claude_is_filled_then_validated_by_january(
    client: httpx.AsyncClient, app: FastAPI, claude: Mcp
) -> None:
    token = await claude.token(FEATURES, "write")
    goal, _ = await call(claude, token, "learning_write_goal", GOAL)
    written, e1 = await call(
        claude,
        token,
        "program_write_program",
        program_body(goal["data"]["id"], start_date=START.isoformat()),
    )
    assert not e1, written
    program_id = written["data"]["id"]
    module = written["data"]["weeks"][0]["modules"][0]

    lesson, e2 = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": module["id"], "markdown": lesson_text("La régression ajuste une droite.")},
    )
    quiz, e3 = await call(
        claude,
        token,
        "quiz_write_quiz",
        {"module_id": module["id"], "title": "Quiz régression", "questions": [QUESTION]},
    )
    moved, e4 = await call(
        claude,
        token,
        "program_update_task",
        {"task_id": module["tasks"][0]["id"], "title": "Lire le chapitre un"},
    )
    assert not (e1 or e2 or e3 or e4), (lesson, quiz, moved)

    ask, is_error = await call(
        claude, token, "program_validate_program", {"program_id": program_id}
    )  # niveau 3 : January confirme dans l'interface
    assert not is_error and ask["data"]["status"] == "pending_confirmation"
    program = (await client.get(f"{API}/programs/{program_id}")).json()
    assert program["status"] == "draft"  # rien n'est validé avant son clic
    assert program["weeks"][0]["modules"][0]["lesson_status"] == "ready"

    confirmed = await claude.http.post(
        f"{API}/mcp/confirmations/{ask['data']['confirmation_id']}/confirm"
    )
    assert confirmed.status_code == 200, confirmed.text
    assert (await client.get(f"{API}/programs/{program_id}")).json()["status"] == "validated"


async def test_read_only_token_cannot_write_a_goal_or_a_program(
    client: httpx.AsyncClient, app: FastAPI, claude: Mcp
) -> None:
    token = await claude.token(FEATURES, "read")

    for name, arguments in (
        ("learning_write_goal", GOAL),
        ("program_write_program", program_body("x")),
    ):
        response = await claude.call(token, name, arguments)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "write_not_allowed"
    assert await sizes(app) == (0, 0, 0, 0, 0, 0)
