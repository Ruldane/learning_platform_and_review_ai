"""L'Éclaireur en mode `company` (D129) : entreprise inconnue sautée, fiche récente reprise, sinon
recherche, trois pages lues au plus, fiche rangée avec l'ATS lu au domaine des liens ; une
recherche refusée ou une sortie invalide laisse la revue continuer sans fiche. Nœud appelé
directement (faux ports, faux modèles), sans réseau."""

import json
from typing import Any

import pytest

from app.agents.nodes.scout.company import COMPANY_REQUEST, NO_BRIEF, UNKNOWN, make_company
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.review_schema import CompanyBrief
from app.agents.tools.web_port import WebSearchResult
from app.core.errors import AppError
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.review_support import BRIEF, FakeWeb, in_untrusted
from tests.support.cv_review import REVIEW_ID, FakeCvReviewStore

GREENHOUSE = "https://boards.greenhouse.io/societefictive"


@pytest.fixture
def emitted(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    written: list[dict[str, Any]] = []
    monkeypatch.setattr("app.agents.runtime.emit.get_stream_writer", lambda: written.append)
    return written


def _said(emitted: list[dict[str, Any]]) -> list[str]:
    return [e["payload"]["text"] for e in emitted if e["__tremplin_event__"] == "agent.message"]


def _models(*replies: str) -> CouncilModels:
    models = CouncilModels()
    models.when("scout", COMPANY_REQUEST, *replies, *[json.dumps(BRIEF)] * 3)
    return models


async def _run(store: FakeCvReviewStore, web: Any, models: CouncilModels) -> CvReviewState:
    deps = GraphDeps(
        "u1",
        "s1",
        models,
        None,  # type: ignore[arg-type]
        RunSettings(300_000, 1, "fr", ("fr",), ""),
        None,  # type: ignore[arg-type]
        AgentPorts(cv_review=store, web=web),
    )
    assert store.analysis is not None
    state: CvReviewState = {
        "review_id": REVIEW_ID,
        "analysis": store.analysis.model_dump(mode="json"),
    }
    return await make_company(deps)(state)


async def test_research_reads_three_pages_and_saves_brief(emitted: list[dict[str, Any]]) -> None:
    store, web, models = FakeCvReviewStore(), FakeWeb(), _models()
    web.urls[2] = GREENHOUSE
    out = await _run(store, web, models)
    assert web.searches == ["Société Fictive"] and len(web.reads) == 3
    assert (
        out["ats"] == "Greenhouse"
        and out["company_brief"] == CompanyBrief.model_validate(BRIEF).model_dump()
    )
    [(name, sources, ats)] = store.companies.values()
    assert name == "Société Fictive" and sources == web.urls[:3] and ats == "Greenhouse"
    [prompt] = [c.prompt for c in models.calls]
    assert in_untrusted(prompt, "Société Fictive édite des assistants")
    assert in_untrusted(prompt, "Texte sur l'entreprise.")
    assert _said(emitted) == ["The company dossier is ready (3 pages read)."]


async def test_unknown_company_is_skipped(emitted: list[dict[str, Any]]) -> None:
    store, web, models = FakeCvReviewStore(company=None), FakeWeb(), _models()
    assert store.analysis is not None
    store.analysis = store.analysis.model_copy(update={"company": None})
    store.posting_urls = [GREENHOUSE]
    out = await _run(store, web, models)
    assert out == {"company": None, "company_brief": None, "ats": "Greenhouse"}
    assert web.searches == [] and models.calls == [] and _said(emitted) == [UNKNOWN]


async def test_fresh_brief_is_reused(emitted: list[dict[str, Any]]) -> None:
    brief = CompanyBrief(summary="Fiche récente.", values=[], stack=[])
    store, web, models = FakeCvReviewStore(company_brief=brief), FakeWeb(), _models()
    out = await _run(store, web, models)
    assert out["company_brief"] == brief.model_dump(mode="json")
    assert web.searches == [] and models.calls == [] and store.companies == {}


class _RefusingWeb(FakeWeb):
    async def search(self, user_id: str, session_id: str, query: str, **_: Any) -> WebSearchResult:
        raise AppError("search_quota", "Plafond de recherches atteint.", 429)


async def test_search_refused_continues_without_brief(emitted: list[dict[str, Any]]) -> None:
    store, models = FakeCvReviewStore(), _models()
    out = await _run(store, _RefusingWeb(), models)
    assert out["company_brief"] is None and store.companies == {} and models.calls == []
    assert NO_BRIEF in _said(emitted)


async def test_invalid_brief_continues_without_brief(emitted: list[dict[str, Any]]) -> None:
    store, models = FakeCvReviewStore(), _models(*["pas du JSON"] * 3)
    out = await _run(store, FakeWeb(), models)
    assert out["company_brief"] is None and store.companies == {} and len(models.calls) == 3
    assert NO_BRIEF in _said(emitted)
