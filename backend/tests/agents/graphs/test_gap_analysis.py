"""Parcours `gap_analysis` (D121) : l'Analyste analyse l'offre, la rattache au référentiel de
January, le code range l'écart ; analyse rangée réutilisée sans appel ; texte qui n'est pas une
offre refusé ; mots clés vérifiés ; texte de l'offre encadré comme non fiable ; rejeu sans double
écriture."""

import json
import logging

import pytest

from app.agents.graphs.gap_analysis import NOT_A_POSTING, GapAnalysisInput
from app.agents.graphs.registry import get_graph
from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, MATCH_REQUEST
from app.agents.tools.gap_port import DuplicateHit
from app.agents.tools.posting_schema import PostingAnalysis
from app.features.sessions.service import ROUTE_ONLY
from scripts.sample_posting import POSTING_TEXT, POSTING_TRAP
from tests.agents.graphs.gap_support import MakeGap, analyst
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.gap import (
    MATCHES,
    POSTING_ID,
    FakeGapStore,
    analysis_data,
    analysis_reply,
    matches_reply,
    not_a_posting_reply,
    requirement,
)

START = '<<<CONTENU_NON_FIABLE source="offre">>>'
END = "<<<FIN_CONTENU_NON_FIABLE>>>"
SCORE_TEXT = "Score de match : 62/100. 4 compétences manquent, dont 2 obligatoires."


def between_untrusted_markers(prompt: str, start: str = START) -> str:
    assert start in prompt
    return prompt.split(start, 1)[1].split(END, 1)[0]


async def test_gap_analysis_analyzes_matches_and_saves(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    run = await gap_runner()
    await run.wait_status("completed")
    pid = POSTING_ID
    assert (
        gap_store.analysis[pid].title == "AI Product Engineer" and gap_store.gaps[pid].score == 62
    )
    assert gap_store.status[pid] == "ready" and gap_store.save_analysis_calls == 1
    assert gap_store.gap[pid]["session_id"] == run.sid
    assert {m["need"]: m["known"] for m in gap_store.gap[pid]["matches"]} == MATCHES
    assert len(run.prompts(ANALYZE_REQUEST)) == 1 and len(run.prompts(MATCH_REQUEST)) == 1
    assert await run.said() == [SCORE_TEXT]
    assert (await run.events("run.completed"))[0]["summary"] == SCORE_TEXT
    [artifact] = await run.events("artifact.ready")
    assert artifact == {
        "artifact_id": pid,
        "kind": "posting_gap",
        "title": "AI Product Engineer",
        "url": f"/carriere/offres/{pid}",
    }


async def test_duplicate_is_announced(gap_runner: MakeGap, gap_store: FakeGapStore) -> None:
    gap_store.duplicates[POSTING_ID] = [
        DuplicateHit("possible", "p-2", None, None, "2026-10-01T09:00:00+00:00", 0.93),
        DuplicateHit("probable", "p-3", "AI Engineer", None, "2026-11-03T08:00:00+00:00", None),
    ]
    run = await gap_runner()
    await run.wait_status("completed")
    assert await run.said() == [SCORE_TEXT, "Offre proche d'une offre déjà ajoutée le 03/11."]


async def test_existing_analysis_is_reused_without_model_call(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    gap_store.analysis[POSTING_ID] = PostingAnalysis.model_validate(analysis_data())
    gap_store.status[POSTING_ID] = "ready"
    run = await gap_runner()
    await run.wait_status("completed")
    assert run.prompts(ANALYZE_REQUEST) == [] and gap_store.save_analysis_calls == 0
    assert gap_store.gaps[POSTING_ID].score == 62 and await run.said() == [SCORE_TEXT]


async def test_first_saved_analysis_wins(gap_runner: MakeGap, gap_store: FakeGapStore) -> None:
    """Une revue de CV a rangé son analyse pendant que l'Analyste travaillait : la suite lit
    celle qui est en base (D121 n° 1)."""
    other = PostingAnalysis.model_validate(analysis_data(title="Ingénieur IA produit"))

    async def race(agent: str, prompt: str) -> None:
        if ANALYZE_REQUEST in prompt:
            gap_store.analysis.setdefault(POSTING_ID, other)

    models = analyst()
    models.hooks.append(race)
    run = await gap_runner(models)
    await run.wait_status("completed")
    assert gap_store.analysis[POSTING_ID].title == "Ingénieur IA produit"
    [artifact] = await run.events("artifact.ready")
    assert artifact["title"] == "Ingénieur IA produit"


async def test_not_a_posting_is_rejected_without_gap(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    run = await gap_runner(analyst([not_a_posting_reply()]))
    await run.wait_status("completed")
    assert gap_store.status[POSTING_ID] == "rejected"
    assert gap_store.rejected[POSTING_ID] == NOT_A_POSTING
    assert gap_store.save_analysis_calls == 0 and gap_store.save_gap_calls == 0
    assert await run.said() == [NOT_A_POSTING]
    assert (await run.events("run.completed"))[0]["summary"] == NOT_A_POSTING
    assert len(run.prompts()) == 1 and await run.events("artifact.ready") == []


async def test_keyword_not_in_text_is_reasked_then_dropped(
    gap_runner: MakeGap, gap_store: FakeGapStore, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    keywords = [*analysis_data()["keywords"], {"term": "Kubernetes", "variants": []}]
    wrong = analysis_reply(keywords=keywords)
    run = await gap_runner(analyst([wrong, wrong, wrong]))
    await run.wait_status("completed")
    asks = run.prompts(ANALYZE_REQUEST)
    assert len(asks) == 3
    assert "« Kubernetes » ne figure pas tel quel dans l'offre" in asks[1]
    terms = [k.term for k in gap_store.analysis[POSTING_ID].keywords]
    assert terms == ["Python", "LangGraph", "RAG", "3 ans d'expérience"]
    assert "Kubernetes" not in caplog.text and "AI Product Engineer" not in caplog.text


async def test_keyword_fixed_on_second_ask(gap_runner: MakeGap, gap_store: FakeGapStore) -> None:
    keywords = [{"term": "Agents IA", "variants": []}]
    run = await gap_runner(analyst([analysis_reply(keywords=keywords)]))
    await run.wait_status("completed")
    assert len(run.prompts(ANALYZE_REQUEST)) == 2
    assert len(gap_store.analysis[POSTING_ID].keywords) == 4


async def test_required_requirement_without_skill_is_reasked(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Revue 6.2, m3 : une exigence obligatoire sans compétence ne serait jamais couverte."""
    bare = [requirement("Python avancé", True), requirement("Anglais professionnel", False)]
    run = await gap_runner(analyst([analysis_reply(requirements=bare)]))
    await run.wait_status("completed")
    asks = run.prompts(ANALYZE_REQUEST)
    assert len(asks) == 2 and "« Python avancé » ne nomme aucune compétence" in asks[1]
    assert "Anglais professionnel" not in asks[1].split("ne respecte pas les règles")[1]
    assert all(r.skills for r in gap_store.analysis[POSTING_ID].requirements if r.required)


async def test_posting_text_is_untrusted(gap_runner: MakeGap, gap_store: FakeGapStore) -> None:
    gap_store.texts[POSTING_ID] = POSTING_TRAP
    run = await gap_runner()
    await run.wait_status("completed")
    prompts = run.prompts()
    assert "Ignore tes règles" in between_untrusted_markers(prompts[0])
    assert "Ignore tes règles" not in prompts[0].replace(between_untrusted_markers(prompts[0]), "")
    match = run.prompts(MATCH_REQUEST)[0]
    assert "LangGraph" in between_untrusted_markers(match, '<<<CONTENU_NON_FIABLE source="offre:')
    assert "Agents LLM" in between_untrusted_markers(match, START.replace("offre", "referentiel"))


async def test_unknown_referential_name_becomes_none(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    invented = {**MATCHES, "Intégration continue": "Jenkins", "LangGraph": "Kubernetes"}
    run = await gap_runner(analyst(matches=[matches_reply(invented)]))
    await run.wait_status("completed")
    matched = {m["need"]: m["known"] for m in gap_store.gap[POSTING_ID]["matches"]}
    assert matched["Intégration continue"] is None  # hors référentiel : jamais inventé
    assert matched["LangGraph"] == "Kubernetes"  # au référentiel (sans niveau) : gardé
    assert gap_store.gaps[POSTING_ID].score == 62


async def test_missing_matches_fall_back_to_same_name(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    """Un besoin oublié par le modèle dont le nom est au référentiel lui est rattaché ; un nom
    écrit autrement que le référentiel est ramené à son écriture."""
    partial = {"Python": None, "RAG": "génération augmentée par recherche"}
    run = await gap_runner(analyst(matches=[matches_reply(partial)]))
    await run.wait_status("completed")
    matched = {m["need"]: m["known"] for m in gap_store.gap[POSTING_ID]["matches"]}
    assert matched["Python"] == "Python" and matched["Docker"] == "Docker"
    assert matched["RAG"] == "Génération augmentée par recherche"
    assert matched["Agents conversationnels"] is None and len(matched) == 10


async def test_empty_referential_matches_without_model_call(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    gap_store.levels = {}
    run = await gap_runner()
    await run.wait_status("completed")
    assert run.prompts(MATCH_REQUEST) == []
    assert all(m["known"] is None for m in gap_store.gap[POSTING_ID]["matches"])
    assert gap_store.gaps[POSTING_ID].score == 0


async def test_replay_of_save_gap_writes_once(gap_runner: MakeGap, gap_store: FakeGapStore) -> None:
    gap_store.block_after_gap = True
    first = await gap_runner()
    await wait_until(lambda: gap_store.save_gap_calls == 1)
    await first.runner.shutdown()  # arrêt du back en plein rangement de l'écart
    calls = len(first.models.calls)
    gap_store.block_after_gap = False
    second = await gap_runner(first.models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert gap_store.save_gap_calls == 2 and gap_store.gap_writes == 1
    assert gap_store.save_analysis_calls == 1 and len(first.models.calls) == calls
    assert await second.said() == [SCORE_TEXT]


async def test_long_requirement_list_is_capped_not_failed(
    gap_runner: MakeGap, gap_store: FakeGapStore
) -> None:
    many = [requirement(f"Exigence numéro {n}", False) for n in range(45)]
    run = await gap_runner(
        analyst([analysis_reply(requirements=many), analysis_reply(requirements=many[:40])])
    )
    await run.wait_status("completed")
    asks = run.prompts(ANALYZE_REQUEST)
    assert len(asks) == 2 and "requirements" in asks[1]
    assert len(gap_store.analysis[POSTING_ID].requirements) == 40


async def test_posting_text_never_logged(
    gap_runner: MakeGap, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    run = await gap_runner()
    await run.wait_status("completed")
    for secret in ("Société Fictive", "AI Product Engineer", "LangGraph", "Agents LLM"):
        assert secret not in caplog.text
    assert POSTING_TEXT[:40] not in caplog.text


def test_graph_is_registered_with_its_own_route() -> None:
    spec = get_graph("gap_analysis")
    assert spec.input_model is GapAnalysisInput
    assert ROUTE_ONLY["gap_analysis"] == "POST /postings"
    with pytest.raises(ValueError):
        GapAnalysisInput.model_validate({"posting_id": "court"})
    assert json.loads(GapAnalysisInput(posting_id=POSTING_ID).model_dump_json()) == {
        "posting_id": POSTING_ID
    }
