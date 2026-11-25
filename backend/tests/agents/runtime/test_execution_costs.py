"""Fin d'une exécution (`run_session`) : les appels coupés sans `on_llm_error` (annulés par
`node_timeout`, une pause ou un arrêt) sont comptés avec des tokens estimés (D117)."""

import asyncio
from collections.abc import Callable
from typing import Any, TypedDict

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GraphSpec
from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.execution import RunContext, run_session
from app.agents.runtime.invoke import call_with_retries, node_timeout
from app.agents.runtime.repositories import LlmCallRepository, SessionRepository
from app.features.settings.service import SettingsRunReader
from app.providers.llm.base import Tier
from tests.agents.runtime.fakes import HangingStream
from tests.agents.runtime.runner_helpers import wait_until


class _State(TypedDict, total=False):
    done: bool


class _Input(BaseModel):
    done: bool = False


class _Models:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        return self.model


def _stuck_graph(seconds: float) -> Callable[[GraphDeps], StateGraph[Any, Any, Any, Any]]:
    """Un nœud qui appelle un modèle sans fin, coupé par `node_timeout(seconds)`."""

    def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
        @node_timeout(seconds)
        async def stuck(state: _State) -> dict[str, Any]:
            model = await deps.models.get_chat_model(deps.user_id, "fast", "tutor")
            await call_with_retries(model, [HumanMessage("h" * 400)], agent="tutor")
            return {"done": True}

        graph: StateGraph[Any, Any, Any, Any] = StateGraph(_State)
        graph.add_node("stuck", stuck)
        graph.add_edge(START, "stuck")
        graph.add_edge("stuck", END)
        return graph

    return build


async def _stuck_session(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
    model: HangingStream,
    seconds: float,
) -> tuple[RunContext, str]:
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(
            graph="stuck", status="running", input={"done": False}
        )
        await db.commit()
    ctx = RunContext(
        session_factory=db_factory,
        bus=bus,
        models=_Models(model),
        checkpointer=checkpointer,
        prices={"m": ModelPrice(1.0, 2.0)},
        graphs={"stuck": GraphSpec("stuck", _Input, _stuck_graph(seconds))},
        run_settings=SettingsRunReader(db_factory),
    )
    return ctx, row.id


async def test_node_timeout_flushes_started_calls(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    model = HangingStream(chunks=3)
    ctx, session_id = await _stuck_session(db_factory, bus, checkpointer, user_id, model, 0.1)
    await run_session(ctx, user_id, session_id, None)
    async with db_factory() as db:
        [call] = await LlmCallRepository(db, user_id).list()
        session = await SessionRepository(db, user_id).get(session_id)
    assert session is not None and session.error is not None
    assert (session.status, session.error["code"]) == ("failed", "node_timeout")
    assert call.estimated and (call.tokens_in, call.tokens_out) == (100, 3)
    assert (call.agent, call.session_id) == ("tutor", session_id)
    assert (session.tokens_in, session.tokens_out) == (100, 3)


async def test_cancelled_run_flushes_started_calls(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    """Revue 6.1, m1 : pause, annulation ou arrêt (`CancelledError` dans la tâche) : l'appel en
    cours est compté, l'annulation remonte, le statut reste celui de l'appelant."""
    model = HangingStream(chunks=3)
    ctx, session_id = await _stuck_session(db_factory, bus, checkpointer, user_id, model, 60)
    task = asyncio.create_task(run_session(ctx, user_id, session_id, None))
    await wait_until(lambda: model.waiting)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with db_factory() as db:
        [call] = await LlmCallRepository(db, user_id).list()
        session = await SessionRepository(db, user_id).get(session_id)
    assert call.estimated and (call.tokens_in, call.tokens_out) == (100, 3)
    assert session is not None and session.status == "running"
