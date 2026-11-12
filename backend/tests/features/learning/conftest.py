"""Matériel des tests de la feature `learning` : l'app réelle (lifespan, runner, vrai port du
Conseil `AgentCouncilStore`) avec deux parcours de remplacement. Le Conseil de test écrit ses
lots et son tableau par le port, puis passe par les vrais nœuds du choix (`ask_choice`,
`route_choice`, `finalize`) ; `program_builder` de test s'arrête sur sa question de validation.
Aucun appel LLM ni réseau."""

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.graphs.learning_council import LearningCouncilInput
from app.agents.graphs.program_builder import ProgramBuilderInput
from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.nodes import council_choice
from app.agents.nodes.council_choice import ask_choice, make_finalize, route_choice
from app.agents.runtime.deps import GraphDeps
from app.agents.state.learning_council import CouncilState
from app.agents.state.program_builder import ProgramState
from app.agents.tools.council_port import ProposalDraft
from app.core.errors import AppError
from tests.sessions_support import use_test_runtime, wait_status

GOALS = "/api/v1/goals"
GOAL_TEXT = "Devenir AI product engineer"


@dataclass
class Stub:
    """`batches` : lots proposés avant la question ; `hold` : le Conseil attend cet événement
    avant la question (session `running`) ; `resumed` : réponses reçues par `ask_choice` ;
    `batch_ids` : ids de chaque lot ; `program_inputs` : entrées de `program_builder` ;
    `council_failures` / `program_failures` : nombre de sessions qui échouent d'abord (le Conseil
    après son lot, avant la question ; `program_builder` avant toute écriture)."""

    batches: int = 1
    hold: asyncio.Event | None = None
    council_failures: int = 0
    program_failures: int = 0
    resumed: list[Any] = field(default_factory=list)
    batch_ids: dict[int, list[str]] = field(default_factory=dict)
    program_inputs: list[dict[str, Any]] = field(default_factory=list)


STUB = Stub()


def _draft(name: str) -> ProposalDraft:
    return ProposalDraft(
        name=name,
        promise="Une promesse assez longue pour le schéma.",
        duration_weeks=8,
        weekly_hours=6,
        skills=["Python", "LLM"],
        final_project="Un projet final complet et démontrable.",
        tradeoffs=["Moins de théorie"],
    )


def _council(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    council = deps.ports.council

    async def propose(state: CouncilState) -> CouncilState:
        batch, goal_id = state.get("batch", 0) + 1, state["goal_id"]
        drafts = [_draft(f"Parcours {batch}.{rank}") for rank in (1, 2, 3)]
        refs = await council.save_proposals(
            deps.user_id, deps.session_id, goal_id, batch=batch, proposals=drafts
        )
        await council.save_board(
            deps.user_id,
            deps.session_id,
            goal_id,
            step=batch,
            kind="comparison",
            title="Comparaison des parcours",
            mermaid="flowchart LR\n  A --> B",
        )
        STUB.batch_ids[batch] = [ref.proposal_id for ref in refs]
        lot = [{"proposal_id": r.proposal_id, "rank": r.rank, "name": r.name} for r in refs]
        return {"batch": batch, "round": batch, "proposals": lot}

    def after_propose(state: CouncilState) -> str:
        return "propose" if state["batch"] < STUB.batches else "gate"

    async def gate(state: CouncilState) -> CouncilState:
        if STUB.hold is not None:
            await STUB.hold.wait()
        if STUB.council_failures > 0:
            STUB.council_failures -= 1
            raise AppError("structured_output_invalid", "Sortie du modèle invalide.", 502)
        return {}

    graph = StateGraph(CouncilState)
    for name, node in [("propose", propose), ("round_start", propose), ("gate", gate)]:
        graph.add_node(name, node)
    graph.add_node("ask_choice", ask_choice)
    graph.add_node("finalize", make_finalize(deps))
    graph.add_edge(START, "propose")
    graph.add_conditional_edges("propose", after_propose, ["propose", "gate"])
    graph.add_conditional_edges("round_start", after_propose, ["propose", "gate"])
    graph.add_edge("gate", "ask_choice")
    graph.add_conditional_edges(
        "ask_choice", route_choice, ["ask_choice", "round_start", "finalize"]
    )
    graph.add_edge("finalize", END)
    return graph


def _program(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def wait_validation(state: ProgramState) -> ProgramState:
        STUB.program_inputs.append(dict(state))
        if STUB.program_failures > 0:
            STUB.program_failures -= 1
            raise AppError("structured_output_invalid", "Sortie du modèle invalide.", 502)
        interrupt({"kind": "validate_program", "question": "Valider ?", "options": []})
        return {}

    graph = StateGraph(ProgramState)
    graph.add_node("wait_validation", wait_validation)
    graph.add_edge(START, "wait_validation")
    graph.add_edge("wait_validation", END)
    return graph


@pytest.fixture(autouse=True)
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[Stub]:
    """Avant l'app (autouse) : parcours de remplacement et faux LLM pour le lifespan."""
    global STUB
    STUB = Stub()
    use_test_runtime(monkeypatch)
    monkeypatch.setitem(
        GRAPHS, "learning_council", GraphSpec("learning_council", LearningCouncilInput, _council)
    )
    monkeypatch.setitem(
        GRAPHS, "program_builder", GraphSpec("program_builder", ProgramBuilderInput, _program)
    )
    real = council_choice.interrupt

    def recording(value: Any) -> Any:
        answer = real(value)
        STUB.resumed.append(answer)
        return answer

    monkeypatch.setattr(council_choice, "interrupt", recording)
    yield STUB
    if STUB.hold is not None:
        STUB.hold.set()


@dataclass
class Waiting:
    goal_id: str
    sid: str
    ids: list[str]  # dernier lot, par rang


async def start_goal(client: httpx.AsyncClient, text: str = GOAL_TEXT) -> tuple[str, str]:
    r = await client.post(GOALS, json={"text": text})
    assert r.status_code == 201, r.text
    return r.json()["goal"]["id"], r.json()["session_id"]


async def proposal_ids(client: httpx.AsyncClient, goal_id: str) -> list[str]:
    return [p["id"] for p in (await client.get(f"{GOALS}/{goal_id}/proposals")).json()]


async def wait_choice(client: httpx.AsyncClient, text: str = GOAL_TEXT) -> Waiting:
    goal_id, sid = await start_goal(client, text)
    view = await wait_status(client, sid, "waiting_user")
    assert view["pending_interrupt"]["kind"] == "choose_path"
    return Waiting(goal_id, sid, await proposal_ids(client, goal_id))


@pytest.fixture
async def council_waiting_choice(client: httpx.AsyncClient) -> Waiting:
    return await wait_choice(client)


async def count_sessions(client: httpx.AsyncClient, graph: str) -> int:
    return len((await client.get("/api/v1/sessions", params={"graph": graph})).json())


async def chosen_ids(client: httpx.AsyncClient, goal_id: str) -> set[str]:
    rows = (await client.get(f"{GOALS}/{goal_id}/proposals")).json()
    return {p["id"] for p in rows if p["chosen"]}


def next_monday(weeks: int = 1) -> str:
    """Un lundi à venir (`weeks` semaines après le prochain), au format ISO."""
    today = date.today()
    return (today + timedelta(days=7 - today.weekday() + 7 * (weeks - 1))).isoformat()


def me(app: FastAPI) -> str:
    user_id: str = app.state.local_user_id
    return user_id
