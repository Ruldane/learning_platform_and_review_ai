"""Nœuds de l'Éclaireur pris un par un (plafonds, rejeu d'un nœud, schémas, entrée) : vraie base,
faux moteurs, aucun réseau."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.graphs.registry import get_graph
from app.agents.graphs.web_research import WebResearchInput
from app.agents.nodes.scout import (
    MAX_PAGES_PER_RUN,
    SearchPlan,
    SourceScore,
    make_read,
    make_search,
)
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.run_settings import RunSettings
from app.features.research.repository import SourceRepository
from tests.agents.graphs.web_support import (
    SCORE_82,
    URL_A,
    URL_B,
    MakeWeb,
    Web,
    document,
    script_web,
)
from tests.features.research.conftest import set_settings

MARKER = "<<<CONTENU_NON_FIABLE"
END = "<<<FIN_CONTENU_NON_FIABLE>>>"


def test_score_total_adds_five_bounded_criteria() -> None:
    parsed = SourceScore.model_validate_json(SCORE_82)
    assert parsed.total == 82 and parsed.criteria["authority"] == 25
    for field, over in (
        ("authority", 31),
        ("freshness", 21),
        ("depth", 21),
        ("author", 16),
        ("pedagogy", 16),
        ("pedagogy", -1),
    ):
        data = {**json.loads(SCORE_82), field: over}
        with pytest.raises(ValidationError):
            SourceScore.model_validate(data)


async def test_search_node_stops_cleanly_when_quota_is_reached_midway(
    make_web_runner: MakeWeb, user_id: str, emitted: list[dict[str, object]]
) -> None:
    web = await make_web_runner([])
    script_web(web)
    await set_settings(web.factory, user_id, search_max_queries=1)
    deps = _deps(web, user_id)
    state: Any = {
        "queries": [
            {"text": "attention multi-têtes", "lang": "fr"},
            {"text": "multi-head attention", "lang": "en"},
        ]
    }
    found = await make_search(deps)(state)
    assert [h["url"] for h in found["hits"]] == [
        URL_A,
        URL_B,
    ]  # la 2e requête a buté sur le plafond
    assert len(web.search.calls) == 1
    kinds = [e["__tremplin_event__"] for e in emitted]
    assert kinds.count("tool.called") == 2 and kinds.count("tool.result") == 2


def _deps(web: Web, user_id: str, session_id: str = "s1") -> GraphDeps:
    return GraphDeps(
        user_id,
        session_id,
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        RunSettings(300_000, 2, "fr", ("fr",), ""),
        web.factory,
        web.memory_gateway,
        web.gateway,
    )


async def test_search_and_read_nodes_replayed_do_not_recount(
    make_web_runner: MakeWeb, user_id: str, emitted: list[dict[str, object]]
) -> None:
    web = await make_web_runner([])
    script_web(web)
    deps = _deps(web, user_id, "s9")
    queries: Any = {"queries": [{"text": "attention multi-têtes", "lang": "fr"}]}
    first = await make_search(deps)(queries)
    again = await make_search(deps)(queries)  # nœud rejoué après un redémarrage
    assert first == again
    state: Any = {"hits": first["hits"], "urls": []}
    one = await make_read(deps)(state)
    two = await make_read(deps)(state)
    assert one == two and len(one["pages"]) == 2
    async with web.factory() as db:
        assert len(await SourceRepository(db, user_id).list_for_session("s9")) == 2
    assert len(web.search.calls) == 1  # la liste vient du cache, Brave n'est jamais refacturé


async def test_read_node_is_capped_by_pages_per_run_and_session_cap(
    make_web_runner: MakeWeb, user_id: str, emitted: list[dict[str, object]]
) -> None:
    web = await make_web_runner([])
    urls = [f"https://ex{n}.exemple.org/p" for n in range(15)]
    for url in urls:
        web.reader.pages[url] = document(url)
    deps = _deps(web, user_id)
    state: Any = {"hits": [{"url": u, "title": "t", "preferred": False} for u in urls], "urls": []}
    out = await make_read(deps)(state)
    assert len(out["pages"]) == MAX_PAGES_PER_RUN
    await set_settings(web.factory, user_id, search_max_pages=3)
    out = await make_read(_deps(web, user_id, "s2"))(state)
    assert len(out["pages"]) == 3


def test_scout_is_a_fast_agent_with_a_prompt_and_the_graph_is_registered() -> None:
    assert get_agent("scout").tier == "rapide"
    assert get_graph("web_research").input_model is WebResearchInput


def test_web_research_input_is_validated() -> None:
    assert WebResearchInput(query="attention").urls == []
    for bad in (
        {},
        {"query": "a"},
        {"query": "x" * 301},
        {"query": "ok", "urls": ["ftp://x.org"]},
        {"query": "ok", "urls": ["https://x.org"] * 6},
    ):
        with pytest.raises(ValueError):
            WebResearchInput.model_validate(bad)


def test_search_plan_is_bounded() -> None:
    queries = [{"text": f"requête {n}", "lang": "fr"} for n in range(7)]
    for bad in ({"queries": []}, {"queries": queries}, {"queries": [{"text": "ok", "lang": "FR"}]}):
        with pytest.raises(ValidationError):
            SearchPlan.model_validate(bad)
