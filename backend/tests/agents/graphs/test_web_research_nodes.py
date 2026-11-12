"""Nœuds de l'Éclaireur pris un par un (plafonds, rejeu d'un nœud, schémas, entrée) : vraie base,
faux moteurs, aucun réseau."""

import asyncio
import json
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from app.agents.graphs.registry import get_graph
from app.agents.graphs.web_research import WebResearchInput
from app.agents.nodes.scout import (
    MAX_PAGES_PER_RUN,
    SearchPlan,
    SourceScore,
    make_judge,
    make_read,
    make_search,
)
from app.agents.nodes.scout.assess import (
    JUDGE_TIMEOUT_S,
    PAGE_JUDGE_TIMEOUT_S,
    UNSCORED_REASON,
)
from app.agents.nodes.scout.models import MAX_EXTRA_URLS, MAX_PAGES_JUDGED
from app.agents.registry import get_agent
from app.agents.runtime.deps import ChatModelSource, GraphDeps
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.core.errors import AppError
from app.features.research.repository import SourceRepository
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeChatModel, _Script
from tests.agents.graphs.web_support import (
    SCORE_41,
    SCORE_82,
    URL_A,
    URL_B,
    MakeWeb,
    Web,
    document,
    script_web,
)
from tests.agents.runtime.runner_helpers import fake_llm_with_provider
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


def _deps(
    web: Web, user_id: str, session_id: str = "s1", models: ChatModelSource | None = None
) -> GraphDeps:
    return GraphDeps(
        user_id,
        session_id,
        models,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        RunSettings(300_000, 2, "fr", ("fr",), ""),
        web.factory,
        AgentPorts(memory=web.memory_gateway, web=web.gateway),
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


# --- `judge` rejoué et délai par page (reliquat de la phase 3, D82) ----------------------------

_TWO_HITS: Any = {
    "hits": [{"url": u, "title": "t", "preferred": False} for u in (URL_A, URL_B)],
    "urls": [],
}


def _found(emitted: list[dict[str, object]]) -> list[object]:
    return [e["payload"] for e in emitted if e["__tremplin_event__"] == "source.found"]


async def test_replayed_judge_does_not_call_model_again(
    make_web_runner: MakeWeb, user_id: str, emitted: list[dict[str, object]]
) -> None:
    """Arrêt après `judge`, puis `read` et `judge` rejoués dans la même session (reprise, ou
    seconde recherche du Conseil) : la lecture rend le verdict déjà posé, `judge` le réémet à
    l'identique sans rappeler le modèle."""
    web = await make_web_runner([])
    script_web(web)
    models, fake = fake_llm_with_provider([SCORE_82, SCORE_41])
    deps = _deps(web, user_id, "s5", models)
    pages = (await make_read(deps)(_TWO_HITS))["pages"]
    assert [p["verdict"] for p in pages] == [None, None]
    first = await make_judge(deps)({"pages": pages})
    assert len(fake.received) == 2
    first_found = _found(emitted)
    emitted.clear()
    again = (await make_read(deps)(_TWO_HITS))["pages"]
    assert [p["verdict"]["verdict"] for p in again] == ["kept", "rejected"]
    second = await make_judge(deps)({"pages": again})
    assert len(fake.received) == 2  # aucun nouvel appel au modèle
    assert second == first and _found(emitted) == first_found


class _SlowFirstChat(FakeChatModel):
    """Le premier appel ne répond jamais (jusqu'à son annulation), les suivants suivent le
    script."""

    started: list[int]

    async def _agenerate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> Any:
        self.started.append(1)
        if len(self.started) == 1:
            await asyncio.Event().wait()
        return self._generate(messages)


class _SlowFirst:
    def __init__(self, replies: list[str]) -> None:
        self.received: list[list[BaseMessage]] = []
        self._script = _Script(replies, self.received)
        self.started: list[int] = []

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        meta = {"tremplin_provider": "fake", "tremplin_model": "modele-test"}
        return _SlowFirstChat(script=self._script, metadata=meta, started=self.started)


async def test_slow_page_score_is_rejected_without_failing_session(
    make_web_runner: MakeWeb,
    user_id: str,
    emitted: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.agents.nodes.scout.assess.PAGE_JUDGE_TIMEOUT_S", 0.05)
    web = await make_web_runner([])
    script_web(web)
    deps = _deps(web, user_id, "s6", _SlowFirst([SCORE_82]))
    pages = (await make_read(deps)(_TWO_HITS))["pages"]
    out = await make_judge(deps)({"pages": pages})
    verdicts = {v["url"]: (v["verdict"], v["score"]) for v in out["verdicts"]}
    assert verdicts == {URL_A: ("rejected", None), URL_B: ("kept", 82)}
    async with web.factory() as db:
        rows = {r.url: r for r in await SourceRepository(db, user_id).list_for_session("s6")}
    assert (rows[URL_A].verdict, rows[URL_A].reason) == ("rejected", UNSCORED_REASON)


async def test_judge_fails_when_every_page_is_too_slow(
    make_web_runner: MakeWeb,
    user_id: str,
    emitted: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.agents.nodes.scout.assess.PAGE_JUDGE_TIMEOUT_S", 0.05)
    web = await make_web_runner([])
    script_web(web, urls=(URL_A,))
    deps = _deps(web, user_id, "s7", _SlowFirst([]))
    hits: Any = {"hits": [{"url": URL_A, "title": "t", "preferred": False}], "urls": []}
    pages = (await make_read(deps)(hits))["pages"]
    with pytest.raises(AppError) as exc:
        await make_judge(deps)({"pages": pages})
    assert exc.value.code == "page_judge_timeout" and exc.value.status_code == 504


def test_judge_node_leaves_each_page_its_full_delay() -> None:
    """Une page lente est écartée seule : le délai du nœud couvre toutes les pages notables."""
    assert JUDGE_TIMEOUT_S >= MAX_PAGES_JUDGED * PAGE_JUDGE_TIMEOUT_S
    assert MAX_PAGES_JUDGED == MAX_PAGES_PER_RUN + MAX_EXTRA_URLS
    with pytest.raises(ValidationError):
        WebResearchInput(query="ok", urls=["https://x.org/a"] * (MAX_EXTRA_URLS + 1))  # type: ignore[list-item]
