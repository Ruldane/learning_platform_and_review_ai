"""`GraphSpec.recursion_limit` (D160) : un parcours à boucles fixe sa limite de pas au lancement ;
sans limite, la bibliothèque décide. Le parcours `market_radar` déclare 38 (D159)."""

from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.execution import RunContext, run_session
from app.agents.runtime.repositories import SessionRepository
from app.features.settings.service import SettingsRunReader


class _State(TypedDict, total=False):
    turns: int


class _Input(BaseModel):
    turns: int = 0


def _looping(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    """Une boucle de 10 passages : 10 pas, plus sa fin."""

    async def step(state: _State) -> _State:
        return {"turns": state.get("turns", 0) + 1}

    def again(state: _State) -> str:
        return "step" if state.get("turns", 0) < 10 else END

    graph: StateGraph[Any, Any, Any, Any] = StateGraph(_State)
    graph.add_node("step", step)
    graph.add_edge(START, "step")
    graph.add_conditional_edges("step", again, ["step", END])
    return graph


async def _status(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
    limit: int | None,
) -> tuple[str, str | None]:
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(graph="loop", status="running", input={})
        await db.commit()
    spec = GraphSpec("loop", _Input, _looping, recursion_limit=limit)
    ctx = RunContext(
        session_factory=db_factory,
        bus=bus,
        models=None,  # type: ignore[arg-type]  # aucun modèle appelé
        checkpointer=checkpointer,
        prices={"m": ModelPrice(1.0, 2.0)},
        graphs={"loop": spec},
        run_settings=SettingsRunReader(db_factory),
    )
    await run_session(ctx, user_id, row.id, None)
    async with db_factory() as db:
        session = await SessionRepository(db, user_id).get(row.id)
    assert session is not None
    return session.status, (session.error or {}).get("code")


async def test_loop_stops_at_the_declared_recursion_limit(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    status, code = await _status(db_factory, bus, checkpointer, user_id, 5)
    assert status == "failed" and code is not None


async def test_loop_without_a_limit_uses_the_library_default(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    assert await _status(db_factory, bus, checkpointer, user_id, None) == ("completed", None)


async def test_loop_within_the_limit_completes(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    assert await _status(db_factory, bus, checkpointer, user_id, 20) == ("completed", None)


def test_market_radar_declares_its_limit() -> None:
    assert GRAPHS["market_radar"].recursion_limit == 38
    assert all(
        spec.recursion_limit is None for name, spec in GRAPHS.items() if name != "market_radar"
    )
