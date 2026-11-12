"""Ports des agents regroupés (`AgentPorts`, D82) : `GraphDeps.memory` et `.web` en viennent, le
runner les passe tels quels aux parcours."""

from collections.abc import Sequence
from typing import Any, TypedDict

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GraphSpec
from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.ports import NO_PORTS, AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.memory_port import NO_MEMORY
from app.agents.tools.web_port import NO_WEB, PageRead, SourceVerdictView, WebLimits
from app.agents.tools.web_port import WebSearchResult as Found
from app.core.errors import AppError
from app.features.settings.service import SettingsRunReader
from tests.agents.runtime.runner_helpers import all_events, fake_llm, wait_status


class _Web:
    """Port web minimal : seules les limites servent ici."""

    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> Found:
        raise AssertionError("inutile ici")

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        raise AssertionError("inutile ici")

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        raise AssertionError("inutile ici")

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        return {}

    async def limits(self, user_id: str) -> WebLimits:
        return WebLimits(("de", "it"), (), 3, 4)


def _deps(ports: AgentPorts = NO_PORTS) -> GraphDeps:
    return GraphDeps(
        "u1",
        "s1",
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        RunSettings(300_000, 3, "fr", ("fr",), ""),
        None,  # type: ignore[arg-type]
        ports,
    )


async def test_graph_deps_memory_and_web_come_from_ports() -> None:
    ports = AgentPorts(web=_Web())
    deps = _deps(ports)
    assert deps.ports is ports and deps.web is ports.web and deps.memory is ports.memory
    assert deps.memory is NO_MEMORY
    default = _deps()
    assert default.ports is NO_PORTS and default.web is NO_WEB
    with pytest.raises(AppError) as exc:
        await default.web.limits("u1")
    assert exc.value.code == "web_unavailable"


class _State(TypedDict, total=False):
    summary: str


class _NoInput(BaseModel):
    pass


def _reads_ports(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def look(state: _State) -> _State:
        limits = await deps.ports.web.limits(deps.user_id)
        return {"summary": ",".join(limits.languages)}

    graph = StateGraph(_State)
    graph.add_node("look", look)
    graph.add_edge(START, "look")
    graph.add_edge("look", END)
    return graph


async def test_runner_passes_ports_to_graphs(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    user_id: str,
) -> None:
    runner = SessionRunner(
        session_factory=db_factory,
        bus=bus,
        models=fake_llm([]),
        checkpointer=checkpointer,
        prices={"modele-test": ModelPrice(1.0, 2.0)},
        run_settings=SettingsRunReader(db_factory),
        graphs={"ports": GraphSpec("ports", _NoInput, _reads_ports)},
        ports=AgentPorts(web=_Web()),
    )
    try:
        sid = await runner.start(user_id, "ports", {})
        await wait_status(db_factory, user_id, sid, "completed")
    finally:
        await runner.shutdown()
    done = [e for e in await all_events(db_factory, user_id, sid) if e.type == "run.completed"]
    assert done[0].payload.summary == "de,it"  # type: ignore[union-attr]
