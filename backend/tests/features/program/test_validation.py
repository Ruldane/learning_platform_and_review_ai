"""Validation du programme (D88) : idempotente, une version acceptée, compétences « en cours »
reflétées dans la mémoire (jamais baissées), reprise de la session du Stratège qui attend."""

import asyncio
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select

from app.agents.graphs.program_builder import ProgramBuilderInput
from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.nodes.strategist.plan import (
    ask_validation,
    make_finalize,
    make_save,
    route_validation,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.program_builder import ProgramState
from app.db.models.learning import Goal
from app.db.models.program import PlanVersion
from app.db.models.skills import UserSkill
from tests.features.program.conftest import Draft
from tests.features.program.support import (
    API,
    Factory,
    add_goal,
    sample_plan,
    task_id,
    view,
)
from tests.sessions_support import use_test_runtime, wait_status

ME = "moi"


def _builder(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    """`program_builder` sans modèle : le brouillon est donné, le reste est réel (port, nœuds)."""

    async def seed(state: ProgramState) -> ProgramState:
        return {"draft": sample_plan().model_dump(mode="json"), "note": ""}

    graph = StateGraph(ProgramState)
    graph.add_node("seed", seed)
    graph.add_node("save", make_save(deps))
    graph.add_node("ask_validation", ask_validation)
    graph.add_node("finalize", make_finalize(deps))
    graph.add_edge(START, "seed")
    graph.add_edge("seed", "save")
    graph.add_edge("save", "ask_validation")
    graph.add_conditional_edges(
        "ask_validation",
        route_validation,
        {"ask_validation": "ask_validation", "draft": "seed", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph


@pytest.fixture
def stub_builder(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    use_test_runtime(monkeypatch)
    spec = GraphSpec("program_builder", ProgramBuilderInput, _builder)
    monkeypatch.setitem(GRAPHS, "program_builder", spec)
    yield


async def _accepted(factory: Factory, program_id: str) -> list[PlanVersion]:
    async with factory() as db:
        rows = await db.execute(select(PlanVersion).where(PlanVersion.program_id == program_id))
        return [v for v in rows.scalars() if v.accepted_at is not None]


async def test_validate_resumes_builder(
    stub_builder: None, client: httpx.AsyncClient, app: FastAPI
) -> None:
    rows = await add_goal(app.state.session_factory, app.state.local_user_id)
    payload = {
        "goal_id": rows.goal_id,
        "proposal_ids": [rows.proposal_id],
        "start_date": "2026-11-16",
    }
    body = {
        "graph": "program_builder",
        "input": payload,
        "subject_type": "goal",
        "subject_id": rows.goal_id,
    }
    sid = (await client.post(f"{API}/sessions", json=body)).json()["session_id"]
    pending = (await wait_status(client, sid, "waiting_user"))["pending_interrupt"]
    assert pending["kind"] == "validate_program"
    [summary] = (await client.get(f"{API}/programs")).json()
    r = await client.post(f"{API}/programs/{summary['id']}/validate")
    assert r.status_code == 202
    assert r.json() == {"program_id": summary["id"], "status": "draft", "session_id": sid}
    await wait_status(client, sid, "completed")
    program = await view(client, summary["id"])
    assert program["status"] == "validated" and program["session_id"] == sid
    again = await client.post(f"{API}/programs/{summary['id']}/validate")
    assert again.json() == {"program_id": summary["id"], "status": "validated", "session_id": None}
    assert len(await _accepted(app.state.session_factory, summary["id"])) == 1
    async with app.state.session_factory() as db:
        goal = await db.get(Goal, rows.goal_id)
        assert goal is not None and goal.status == "planned"


async def test_double_validate_is_idempotent(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    url = f"{API}/programs/{draft_program.program_id}/validate"
    first, second = await client.post(url), await client.post(url)
    assert first.status_code == second.status_code == 202
    assert (
        first.json()
        == second.json()
        == {
            "program_id": draft_program.program_id,
            "status": "validated",
            "session_id": None,
        }
    )
    [accepted] = await _accepted(app.state.session_factory, draft_program.program_id)
    assert accepted.version == 1  # aucune modification : la version du Stratège est acceptée


async def test_validation_after_moves_accepts_january_version(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire l'article A")
    await client.patch(f"{API}/tasks/{tid}", json={"planned_date": "2026-11-17"})
    await client.post(f"{API}/programs/{draft_program.program_id}/validate")
    [accepted] = await _accepted(app.state.session_factory, draft_program.program_id)
    assert accepted.version == 2 and accepted.reason == "Modifications de January"
    assert accepted.diff is not None and len(accepted.diff["moved"]) == 1
    after = await view(client, draft_program.program_id)
    assert after["version"] == 2 and after["weekday_minutes"] == 120


async def test_concurrent_validations_accept_one_version(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire l'article A")
    await client.patch(f"{API}/tasks/{tid}", json={"planned_date": "2026-11-17"})
    url = f"{API}/programs/{draft_program.program_id}/validate"
    first, second = await asyncio.gather(client.post(url), client.post(url))
    assert first.status_code == second.status_code == 202
    assert first.json()["status"] == second.json()["status"] == "validated"
    [accepted] = await _accepted(app.state.session_factory, draft_program.program_id)
    assert accepted.version == 2
    async with app.state.session_factory() as db:
        count = await db.execute(select(func.count()).select_from(UserSkill))
        assert count.scalar_one() == 2
