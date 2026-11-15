"""Scénario du parcours n° 3 : la lecture scriptée de la phrase passe la vraie validation de
`IntakeDraft` (jour de January, mots de la phrase), la fiche qu'elle décrit ressemble à la fiche
manuelle du parcours (alerte « probable ») sans ressembler à celle de l'offre (simple information),
et la page de l'offre du lien est une offre que l'Analyste scripté lit sans problème."""

import json
from datetime import date

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, analysis_problems
from app.agents.nodes.tracker.intake import (
    INTAKE_REQUEST,
    IntakeReading,
    parse_vars,
    reading_schema,
)
from app.agents.prompts.loader import render_prompt
from app.agents.tools.applications_port import IntakeDraft
from app.agents.tools.posting_schema import PostingAnalysis, enough_text
from app.features.postings.service.rules import PROBABLE_TITLE, title_similarity
from app.providers.web.base import WebDocument
from scripts.sample_posting import POSTING_TEXT
from tests.e2e import applications_script
from tests.e2e.applications_script import (
    ANALYSIS_TITLE,
    PAGE_TEXT,
    POSTING_URL,
    REFERENCE,
    SENTENCE,
    TITLE,
    applications_scripts,
    intake_reading,
    script_posting_web,
    yesterday,
)
from tests.e2e.cv_script import COMPANY, cv_scripts
from tests.e2e.scripted_models import ScriptedModels, merge_scripts
from tests.support.memory import FakeWebReader

TODAY = date(2026, 11, 15)
MANUAL_TITLE = "Développeuse IA (H/F)"  # la fiche manuelle du parcours (préflight P11)


def _prompt(today: date = TODAY) -> str:
    return render_prompt("tracker", **parse_vars(SENTENCE, today, "fr"))


async def _read(today: date = TODAY) -> str:
    models = ScriptedModels(applications_scripts())
    model = await models.get_chat_model("u1", "rapide", agent="tracker")
    reply = await model.ainvoke([SystemMessage(_prompt(today)), HumanMessage(INTAKE_REQUEST)])
    return str(reply.content)


async def test_reading_passes_the_real_validation_of_the_draft() -> None:
    reading = reading_schema(TODAY, SENTENCE).model_validate_json(await _read())
    draft = IntakeDraft.model_validate(reading.model_dump())

    assert (draft.company, draft.title) == (COMPANY, TITLE)
    assert draft.status == "applied"
    assert draft.applied_on == date(2026, 11, 14)  # « hier », lu dans le prompt
    assert (draft.channel, draft.contact_name, draft.notes) == (None, None, None)


async def test_the_day_of_yesterday_follows_the_day_of_the_server() -> None:
    reading = IntakeReading.model_validate_json(await _read(date(2026, 3, 1)))

    assert reading.applied_on == date(2026, 2, 28)
    assert yesterday(_prompt(date(2026, 3, 1))) == "2026-02-28"


async def test_a_reading_the_real_validation_would_refuse_is_caught_here() -> None:
    """Garde-fou de ce test : le contrôle des mots de la phrase refuse bien un poste inventé."""
    invented = json.loads(await _read()) | {"title": "Ingénieure produit"}

    with pytest.raises(ValueError, match="recopié de la phrase"):
        reading_schema(TODAY, SENTENCE).model_validate(invented)


def test_a_prompt_without_yesterday_fails_naming_the_cause() -> None:
    with pytest.raises(RuntimeError, match="hier"):
        intake_reading([HumanMessage("Rien.")])


def test_the_sentence_matches_the_manual_application_but_not_the_posting_ones() -> None:
    # Fiche manuelle « Développeuse IA (H/F) » : « probable » (même entreprise, titre proche).
    assert title_similarity(TITLE, MANUAL_TITLE) >= PROBABLE_TITLE
    # Fiches des offres (celle du parcours, celle du parcours n° 2) : la même entreprise seulement.
    assert title_similarity(TITLE, ANALYSIS_TITLE) < PROBABLE_TITLE
    assert title_similarity(TITLE, "AI Product Engineer") < PROBABLE_TITLE
    # Les deux offres de l'entreprise ne se prennent pas l'une pour l'autre.
    assert title_similarity(ANALYSIS_TITLE, "AI Product Engineer") < PROBABLE_TITLE
    assert title_similarity(ANALYSIS_TITLE, MANUAL_TITLE) < PROBABLE_TITLE


async def test_the_queue_serves_every_sentence_and_retry_of_the_journey() -> None:
    models = ScriptedModels(applications_scripts())
    model = await models.get_chat_model("u1", "rapide", agent="tracker")
    messages = [SystemMessage(_prompt()), HumanMessage(INTAKE_REQUEST)]

    for _ in range(applications_script.LONG):
        await model.ainvoke(messages)

    assert "tracker" not in models.remaining()


def test_the_posting_link_gives_a_page_the_analyst_reads_without_problem() -> None:
    reader = FakeWebReader()
    script_posting_web(reader)
    page = reader.pages[POSTING_URL]
    reply = applications_script.posting_analysis(_asked(page))
    analysis = PostingAnalysis.model_validate_json(reply)

    assert not isinstance(page, Exception)
    assert page.text == PAGE_TEXT != POSTING_TEXT  # distincte de l'offre du parcours n° 2
    assert enough_text(page.text)
    assert (analysis.company, analysis.title) == (COMPANY, ANALYSIS_TITLE)
    assert analysis_problems(analysis, page.text) == []


def _asked(page: object) -> list[BaseMessage]:
    """Le prompt de l'Analyste pour la page lue : le texte de l'offre y figure."""
    assert isinstance(page, WebDocument)
    return [SystemMessage("Consignes."), HumanMessage(f"{ANALYZE_REQUEST}\n{page.text}")]


async def _analyze(models: ScriptedModels, posting: str) -> PostingAnalysis:
    model = await models.get_chat_model("u1", "standard", agent="analyst")
    reply = await model.ainvoke(
        [SystemMessage("Consignes."), HumanMessage(f"{ANALYZE_REQUEST}\n{posting}")]
    )
    return PostingAnalysis.model_validate_json(str(reply.content))


async def test_the_analyst_reads_the_journey_postings_apart_from_the_cv_ones() -> None:
    cv = cv_scripts()
    models = ScriptedModels(merge_scripts(applications_scripts(), cv))

    ours = await _analyze(models, f"{POSTING_TEXT}\n{REFERENCE} (texte collé).")
    theirs = await _analyze(models, POSTING_TEXT)  # l'offre du parcours n° 2, collée telle quelle
    again = await _analyze(models, f"{POSTING_TEXT}\n{REFERENCE} (page du lien).")

    assert [ours.title, theirs.title, again.title] == [
        ANALYSIS_TITLE,
        "AI Product Engineer",
        ANALYSIS_TITLE,
    ]
    assert {ours.company, theirs.company} == {COMPANY}
