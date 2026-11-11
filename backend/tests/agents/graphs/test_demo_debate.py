"""Parcours `demo_debate` de bout en bout (runner, faux fournisseur, base et checkpointer réels)."""

import asyncio

import pytest
from jinja2 import UndefinedError
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.demo_debate import DemoDebateInput
from app.agents.graphs.registry import GRAPHS, get_graph
from app.agents.prompts.loader import render_prompt
from app.agents.registry import AGENTS, get_agent
from app.db.models.agents import LlmCall
from tests.agents.graphs.conftest import Debate, MakeDebate
from tests.agents.runtime.runner_helpers import (
    all_events,
    get_session,
    types,
    wait_idle,
    wait_status,
)

type Factory = async_sessionmaker[AsyncSession]

R = ["Défenseur 1", "Critique 1", "Défenseur 2", "Critique 2", "Défenseur 3", "Critique 3"]
QUESTION = "Quel angle pour le second tour ?"
OPTIONS = [{"value": "concret", "label": "Plus concret"}, {"value": "court", "label": "Plus court"}]


async def _until_asked(d: Debate, db: Factory, user_id: str, sid: str, *, not_id: str = "") -> str:
    """Attend une question en attente (différente de `not_id`) et la fin de la tâche."""
    async with asyncio.timeout(5):
        while True:
            row = await get_session(db, user_id, sid)
            iid = str((row.pending_interrupt or {}).get("interrupt_id", ""))
            if row.status == "waiting_user" and iid and iid != not_id:
                break
            await asyncio.sleep(0.01)
    await wait_idle(d.runner, sid)
    return iid


async def _agents(db: Factory, user_id: str, sid: str, kind: str) -> list[str | None]:
    return [e.agent for e in await all_events(db, user_id, sid) if e.type == kind]


# --- Déroulé ---------------------------------------------------------------------------------


async def test_streams_two_agents_then_asks(make_debate: MakeDebate, db_factory: Factory, user_id):
    d = await make_debate(R[:4])
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    await _until_asked(d, db_factory, user_id, sid)
    t = await types(db_factory, user_id, sid)
    assert t.count("agent.message") == 2 and "agent.token" in t and t[-1] == "interrupt.requested"
    assert await _agents(db_factory, user_id, sid, "agent.started") == [
        "demo_proponent",
        "demo_critic",
    ]
    assert await _agents(db_factory, user_id, sid, "agent.message") == [
        "demo_proponent",
        "demo_critic",
    ]


async def test_interrupt_payload_shape(make_debate: MakeDebate, db_factory: Factory, user_id):
    d = await make_debate(R[:4])
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    await _until_asked(d, db_factory, user_id, sid)
    pending = (await get_session(db_factory, user_id, sid)).pending_interrupt
    assert pending is not None
    assert {k: v for k, v in pending.items() if k != "interrupt_id"} == {
        "kind": "choice",
        "question": QUESTION,
        "options": OPTIONS,
    }


async def test_user_message_and_choice_reach_second_round(
    make_debate: MakeDebate, db_factory: Factory, user_id
):
    d = await make_debate(R[:4])
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    iid = await _until_asked(d, db_factory, user_id, sid)
    assert "Pense aux débutants" not in str(d.fake.received[:2])
    await d.runner.post_message(user_id, sid, "Pense aux débutants")
    await d.runner.resume(user_id, sid, iid, "concret")
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(d.runner, sid)
    assert len(d.fake.received) == 4
    assert "Pense aux débutants" in str(d.fake.received[2])  # Défenseur, tour 2
    assert "Pense aux débutants" in str(d.fake.received[3])  # Critique, tour 2
    assert "Critique 1" in str(d.fake.received[2])  # il répond au Critique
    assert "Défenseur 2" in str(d.fake.received[3])  # le Critique répond nommément
    assert "concret" in str(d.fake.received[2]).lower()
    final = (await all_events(db_factory, user_id, sid))[-1]
    assert final.type == "run.completed"
    assert "apprendre Rust" in final.payload.model_dump()["summary"]


# --- Nombre de tours (réglage debate_rounds) -------------------------------------------------


async def test_one_round_never_asks(make_debate: MakeDebate, db_factory: Factory, user_id):
    d = await make_debate(R[:2], rounds=1)
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(d.runner, sid)
    t = await types(db_factory, user_id, sid)
    assert t.count("agent.message") == 2 and "interrupt.requested" not in t


async def test_three_rounds_ask_twice_and_stop_after_the_last(
    make_debate: MakeDebate, db_factory: Factory, user_id
):
    d = await make_debate(R, rounds=3)
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    first = await _until_asked(d, db_factory, user_id, sid)
    await d.runner.resume(user_id, sid, first, "court")
    second = await _until_asked(d, db_factory, user_id, sid, not_id=first)
    pending = (await get_session(db_factory, user_id, sid)).pending_interrupt
    assert pending is not None and pending["question"] != QUESTION
    await d.runner.resume(user_id, sid, second, "concret")
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(d.runner, sid)
    t = await types(db_factory, user_id, sid)
    assert t.count("agent.message") == 6 and t.count("interrupt.requested") == 2
    assert len(d.fake.received) == 6


# --- Aucun effet de bord avant interrupt() ---------------------------------------------------


async def test_ask_user_has_no_side_effect_before_interrupt(
    make_debate: MakeDebate, db_factory: Factory, user_id
):
    """Le nœud est rejoué depuis son début à la reprise (et après un redémarrage) : tout effet
    avant `interrupt()` serait publié deux fois."""
    d = await make_debate(R[:4])
    sid = await d.runner.start(user_id, "demo_debate", {"topic": "apprendre Rust"})
    iid = await _until_asked(d, db_factory, user_id, sid)
    before = [e.seq for e in await all_events(db_factory, user_id, sid)]
    await d.runner.shutdown()
    d2 = await make_debate(R[2:4])
    assert await d2.runner.recover_on_startup() == []
    assert [e.seq for e in await all_events(db_factory, user_id, sid)] == before
    await d2.runner.resume(user_id, sid, iid, "court")  # le nœud repart de zéro
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(d2.runner, sid)
    events = await all_events(db_factory, user_id, sid)
    assert [e.type for e in events].count("interrupt.requested") == 1
    assert [e.type for e in events[len(before) :]][0] == "agent.started"  # rien entre les deux
    async with db_factory() as db:
        calls = await db.scalar(select(func.count()).select_from(LlmCall))
    assert calls == 4


# --- Enregistrement, entrée, prompts ---------------------------------------------------------


def test_agents_and_graph_are_registered():
    assert get_agent("demo_proponent").tier == "rapide"
    assert get_agent("demo_critic").tier == "rapide"
    assert get_graph("demo_debate") is GRAPHS["demo_debate"]
    assert GRAPHS["demo_debate"].input_model is DemoDebateInput
    assert {"demo_proponent", "demo_critic"} <= set(AGENTS)


@pytest.mark.parametrize("topic", ["ab", "x" * 201])
def test_input_topic_length_is_validated(topic: str):
    with pytest.raises(ValidationError):
        DemoDebateInput(topic=topic)


VARS = {
    "topic": "apprendre Rust",
    "round": 2,
    "rounds": 3,
    "previous": "Texte de l'autre agent",
    "notes": ["Pense aux débutants"],
    "angle": "concret",
}


@pytest.mark.parametrize("agent", ["demo_proponent", "demo_critic"])
def test_prompts_render_with_their_variables(agent: str):
    out = render_prompt(agent, **VARS)
    assert "apprendre Rust" in out and "Texte de l'autre agent" in out
    assert "Réponds nommément à January sur" in out and "Pense aux débutants" in out
    assert "80 mots" in out


@pytest.mark.parametrize("agent", ["demo_proponent", "demo_critic"])
def test_prompts_without_notes_nor_angle_omit_those_parts(agent: str):
    out = render_prompt(agent, **{**VARS, "notes": [], "angle": None, "previous": ""})
    assert "January" not in out


def test_critic_answers_the_proponent_by_name():
    assert "Défenseur" in render_prompt("demo_critic", **VARS)


@pytest.mark.parametrize("agent", ["demo_proponent", "demo_critic"])
def test_prompts_require_every_variable(agent: str):
    with pytest.raises(UndefinedError):
        render_prompt(agent, topic="x")
