"""Scénario du parcours n° 2 : ses réponses sont celles que les règles du code laissent passer, avec
les verdicts voulus (une proposition à confirmer, un mot clé vers l'écart), et ses files couvrent
chaque appel du parcours. Le CV du parcours (écrit en TypeScript) a la même empreinte que celui de
`scripts/sample_cv.py`."""

import hashlib
import json

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, MATCH_REQUEST, analysis_problems
from app.agents.nodes.archivist_profile import check
from app.agents.nodes.designer import DRAFT_REQUEST, SAMPLE_REQUEST
from app.agents.nodes.designer_steps import invented_lines
from app.agents.nodes.review_common import PROPOSE_REQUEST, proposal_issues
from app.agents.state.cv_capture import CvCaptureState
from app.agents.tools.cv_schema import CvContent, MasterProfileData, assign_fact_ids
from app.agents.tools.cv_validator import validate
from app.agents.tools.gap_port import SkillMatches
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.profile_check import blank_facts
from app.agents.tools.review_schema import AtsReading, CompanyBrief, Confrontation, RecruiterReading
from app.agents.tools.template_schema import TemplateSpec, template_problems
from app.features.cv.service.profile_merge import merge_draft
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from scripts.sample_cv import make_cv_pdf
from scripts.sample_posting import POSTING_TEXT
from tests.e2e import cv_script
from tests.e2e.cv_script import cv_scripts, dispatch
from tests.e2e.scripted_models import Reply, ScriptedModels, merge_scripts
from tests.support.cv_templates import sample_reply
from tests.support.gap import analysis_reply

# Empreinte du PDF : la même valeur est vérifiée côté TypeScript (`e2e/support/sampleCv.ts`).
SAMPLE_CV_SHA256 = "3924eb0157a1efb94b280d1d6ddbd48244fbc4fb28dcbc2860090f10024ea9b0"


async def _cv_text() -> str:
    """Ce que l'Archiviste lit du CV : les blocs visibles de la mise en page réelle, dans l'ordre
    du flux."""
    layout = await LocalPdfLayoutExtractor().extract_layout(make_cv_pdf())
    pages = [
        "\n".join(b.text for b in p.blocks if not b.invisible and b.text.strip())
        for p in layout.pages
    ]
    return "\n\n".join(pages)


async def _profile() -> MasterProfileData:
    """Le profil validé de January : le brouillon de l'Archiviste, contrôlé puis numéroté."""
    found = MasterProfileData.model_validate_json(cv_script.profile())
    state: CvCaptureState = {
        "draft": assign_fact_ids(blank_facts(found)).model_dump(mode="json"),
        "sources": [{"kind": "cv", "text": await _cv_text()}],
    }
    checked = check(state)
    assert checked["dropped"] == []  # rien n'est retiré : tout est dans le CV
    return merge_draft(MasterProfileData.model_validate(checked["draft"]), None, set())


def test_typescript_sample_cv_has_the_same_fingerprint() -> None:
    assert hashlib.sha256(make_cv_pdf()).hexdigest() == SAMPLE_CV_SHA256


async def test_profile_keeps_every_fact_and_gets_the_ids_the_proposals_cite() -> None:
    profile = await _profile()

    assert [x.id for x in profile.experiences] == ["x1", "x2"]
    ids = [line.id for x in profile.experiences for line in x.achievements]
    assert ids == ["x1a1", "x1a2", "x2a1", "x2a2"]
    assert profile.identity.name == cv_script.F["name"]


async def test_proposals_get_the_wanted_verdicts() -> None:
    profile = await _profile()
    analysis = PostingAnalysis.model_validate_json(analysis_reply())
    ats = AtsReading.model_validate_json(cv_script.ats_reading())
    recruiter = RecruiterReading.model_validate_json(cv_script.recruiter_reading())

    assert proposal_issues(ats.items, profile, "a") == []
    assert proposal_issues(recruiter.items, profile, "r") == []
    verdicts = {p.ref: validate(p, profile, analysis) for p in [*ats.items, *recruiter.items]}
    assert {ref: v.status for ref, v in verdicts.items()} == {
        "a1": "ok",
        "a2": "to_confirm",
        "a3": "to_gap",
        "r1": "ok",
    }
    assert verdicts["a3"].gap_terms == [cv_script.GAP_TERM]


async def test_designer_copy_is_verbatim_and_the_description_valid() -> None:
    original = await _cv_text()
    sample = CvContent.model_validate_json(sample_reply())
    spec = TemplateSpec.model_validate_json(cv_script.design())

    assert invented_lines(sample, original) == []
    assert template_problems(spec, [cv_script.FONT, "Lato"]) == []


def test_posting_analysis_has_no_problem_and_company_brief_is_valid() -> None:
    analysis = PostingAnalysis.model_validate_json(analysis_reply())

    assert analysis_problems(analysis, POSTING_TEXT) == []
    assert analysis.company == cv_script.COMPANY
    assert CompanyBrief.model_validate_json(cv_script.company_brief()).stack
    assert SkillMatches.model_validate_json(cv_script.NO_MATCHES).items == []
    assert Confrontation.model_validate_json(cv_script.NO_STANCES).stances == []


async def _ask(models: ScriptedModels, agent: str, request: str) -> str:
    model = await models.get_chat_model("u1", "standard", agent=agent)
    reply = await model.ainvoke([SystemMessage("Consignes."), HumanMessage(request)])
    return str(reply.content)


async def test_every_call_of_the_journey_has_a_reply() -> None:
    models = ScriptedModels(cv_scripts())
    asked = [
        ("archivist", "Build January's master profile from her documents."),
        ("designer", SAMPLE_REQUEST),
        ("designer", DRAFT_REQUEST),
        ("analyst", ANALYZE_REQUEST),
        ("analyst", MATCH_REQUEST),
        ("scout", "Rédige la fiche de l'entreprise."),
        ("ats_reader", PROPOSE_REQUEST),
        ("recruiter", PROPOSE_REQUEST),
        ("ats_reader", "Prends position sur les propositions de l'autre agent."),
        ("recruiter", "Réponds aux objections sur tes propositions."),
    ]

    for agent, request in asked:
        assert json.loads(await _ask(models, agent, request)) is not None

    assert set(cv_scripts()) == {
        "archivist",
        "designer",
        "analyst",
        "scout",
        "ats_reader",
        "recruiter",
    }


async def test_a_reply_that_does_not_recognize_its_call_names_the_agent() -> None:
    models = ScriptedModels({"analyst": [dispatch("analyst", {ANALYZE_REQUEST: "{}"})]})

    with pytest.raises(RuntimeError, match="agent analyst"):
        await _ask(models, "analyst", "Autre chose.")


async def test_a_shared_agent_serves_each_scenario_in_its_own_order() -> None:
    council: dict[str, list[Reply]] = {
        "scout": [dispatch("scout", {"plan": "p1"}), dispatch("scout", {"note": "p2"})]
    }
    cv: dict[str, list[Reply]] = {"scout": [dispatch("scout", {"fiche": "f1"})], "analyst": ["a"]}
    models = ScriptedModels(merge_scripts(council, cv))

    # La fiche vient avant la fin du Conseil, puis le Conseil reprend : aucun ordre global.
    assert await _ask(models, "scout", "plan") == "p1"
    assert await _ask(models, "scout", "fiche") == "f1"
    assert await _ask(models, "scout", "note") == "p2"
    assert await _ask(models, "analyst", "x") == "a"
    assert models.remaining() == {}


async def test_a_shared_agent_still_fails_on_a_call_no_scenario_expects() -> None:
    council = {"scout": [dispatch("scout", {"plan": "p"})]}
    cv = {"scout": [dispatch("scout", {"fiche": "f"})]}
    models = ScriptedModels(merge_scripts(council, cv))

    with pytest.raises(RuntimeError, match="aucun scénario n'attend cet appel de l'agent scout"):
        await _ask(models, "scout", "autre")
