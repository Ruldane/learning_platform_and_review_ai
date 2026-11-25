"""L'Intervieweur (D145) : lecture des réponses, choix du code (réponse la plus faible, questions
ratées), contrôle des faits de la réponse améliorée, fiches de révision, schémas et registres."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.graphs.interview import InterviewInput
from app.agents.graphs.registry import GRAPHS
from app.agents.nodes.interviewer.context import (
    NO_DOSSIER,
    NO_POSTING,
    dossier_block,
    exchange_text,
    posting_block,
)
from app.agents.nodes.interviewer.debrief import (
    allowed_phrases,
    flagged_terms,
    missed_indices,
    revision_cards,
    weakest_index,
)
from app.agents.nodes.interviewer.turn import parse_reply
from app.agents.registry import AGENTS
from app.agents.runtime.ports import NO_PORTS
from app.agents.tools.interview_port import NO_INTERVIEWS
from app.agents.tools.interview_schema import (
    QUESTIONS_BY_DURATION,
    Debrief,
    Exchange,
    TurnDecision,
    debrief_schema,
    plan_schema,
)
from app.core.errors import AppError
from app.features.sessions.service import ROUTE_ONLY
from tests.agents.graphs.interview_support import debrief_json, expected, plan_json
from tests.support.interviews import COMPANY, TITLE, default_context


def exchange(index: int, note: int, **over: Any) -> Exchange:
    fields: dict[str, Any] = {
        "index": index,
        "question": f"Question {index} sur le poste ?",
        "criterion": "clarity",
        "source": "posting",
        "answer": "Une réponse.",
        "note": note,
    }
    return Exchange(**(fields | over))


def test_exchange_reads_the_codes_from_an_old_checkpoint() -> None:
    previous = exchange(0, 4, criterion="clarte", source="offre")
    assert (previous.criterion, previous.source) == ("clarity", "posting")
    assert previous.answer == "Une réponse."


def test_registries() -> None:
    assert AGENTS["interviewer"].tier == "strong"
    assert GRAPHS["interview"].input_model is InterviewInput
    assert ROUTE_ONLY["interview"] == "POST /applications/{id}/interviews"
    assert NO_PORTS.interviews is NO_INTERVIEWS
    assert QUESTIONS_BY_DURATION == {15: 4, 30: 7, 45: 10}


async def test_unplugged_port_says_so() -> None:
    with pytest.raises(AppError) as unavailable:
        await NO_INTERVIEWS.context("u", "i")
    assert (unavailable.value.code, unavailable.value.status_code) == ("interview_unavailable", 503)
    with pytest.raises(AppError):
        await NO_INTERVIEWS.save_result("u", "s", "i", [], None, [], [])


@pytest.mark.parametrize(
    ("value", "expected_reply"),
    [
        ({"answers": {"answer": "  Ma réponse  "}}, {"action": "answer", "text": "Ma réponse"}),
        ("stop", {"action": "stop"}),
        ({"action": "stop"}, {"action": "stop"}),
        ({"answers": {"answer": "x" * 5000}}, {"action": "answer", "text": "x" * 4000}),
        ("Ma réponse en clair", None),  # une valeur d'option inconnue : la question est reposée
        ({"answers": {"answer": "  "}}, None),
        ({"answers": {"answer": 3}}, None),
        ({"answers": "texte"}, None),
        ({}, None),
        (None, None),
    ],
)
def test_parse_reply(value: Any, expected_reply: dict[str, Any] | None) -> None:
    assert parse_reply(value) == expected_reply


def test_the_code_picks_the_weakest_answer_and_the_missed_questions() -> None:
    exchanges = [exchange(0, 4), exchange(1, 2), exchange(2, 2), exchange(3, 5)]
    assert weakest_index(exchanges) == 1  # la plus ancienne en cas d'égalité
    assert missed_indices(exchanges) == [1, 2]
    assert missed_indices([exchange(0, 3)]) == []


def test_company_and_title_are_allowed_phrases_only() -> None:
    ctx = default_context()
    assert allowed_phrases(ctx) == [TITLE, COMPANY]
    assert allowed_phrases(default_context(analysis=None)) == [TITLE]
    text = f"Pour votre poste de {TITLE} chez {COMPANY}, j'ai travaillé avec Python."
    assert flagged_terms(text, ctx) == []
    assert flagged_terms("J'ai géré 40 personnes avec LangGraph.", ctx) == ["40", "LangGraph"]


def test_cards_cover_the_missed_questions_that_have_points() -> None:
    exchanges = [exchange(0, 5), exchange(1, 1, question="Q" * 400), exchange(2, 2)]
    debrief = Debrief.model_validate_json(debrief_json(missed=[1, 2], expected=expected(1)))
    cards = revision_cards(exchanges, debrief)
    assert [len(c.front) <= 300 for c in cards] == [True]  # le recto est raccourci
    assert cards[0].back == "- Point clé 1 a\n- Point clé 1 b"


def _plan(*texts: str) -> str:
    questions = [{"text": text, "criterion": "clarity", "source": "cv"} for text in texts]
    return json.dumps({"questions": questions})


def test_plan_is_exactly_n_distinct_questions() -> None:
    assert len(plan_schema(4).model_validate_json(plan_json(4)).questions) == 4
    with pytest.raises(ValidationError):
        plan_schema(4).model_validate_json(plan_json(5))
    with pytest.raises(ValidationError, match="identical"):
        plan_schema(2).model_validate_json(_plan("La même ?", "la  même ?"))


def test_long_question_is_shortened_not_refused() -> None:
    [question] = plan_schema(1).model_validate_json(_plan("mot " * 200)).questions
    assert len(question.text) <= 400


def test_turn_decision_bounds() -> None:
    assert TurnDecision(follow_up="  ", note=3).follow_up is None
    assert len(TurnDecision(follow_up="a " * 400, note=3).follow_up or "") <= 300
    for note in (0, 6):
        with pytest.raises(ValidationError):
            TurnDecision(note=note)


@pytest.mark.parametrize(
    "over",
    [
        {"scores": {"clarity": 4, "structure": 3, "role_fit": 4}},  # One score is missing.
        {"scores": {"clarity": 4, "structure": 3, "technical_depth": 6, "role_fit": 4}},
        {"strengths": ["a", "b"]},
        {"fixes": ["a", "b", "c", "d"]},
    ],
)
def test_debrief_needs_four_scores_three_strengths_three_fixes(over: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Debrief.model_validate_json(debrief_json(**over))


def test_debrief_must_cover_the_missed_questions() -> None:
    schema = debrief_schema([1, 2])
    schema.model_validate_json(debrief_json(expected=expected(1, 2)))
    with pytest.raises(ValidationError, match="missed questions"):
        schema.model_validate_json(debrief_json(expected=expected(1)))
    debrief_schema([]).model_validate_json(debrief_json())


def test_prompt_blocks_say_what_is_missing() -> None:
    free = default_context(posting_text=None, analysis=None, dossier=None)
    assert posting_block(free) == NO_POSTING and dossier_block(free) == NO_DOSSIER
    summary = posting_block(default_context(posting_text=None))
    assert TITLE in summary and "<<<UNTRUSTED_CONTENT" in summary


def test_exchange_text_shows_follow_up_and_unanswered_follow_up() -> None:
    text = exchange_text(exchange(2, 3, follow_up="Et ensuite ?"), with_note=False)
    assert "[index 2]" in text and "Et ensuite ?" in text and "(no answer)" in text
    assert "Note interne" not in text


def test_pending_follow_up_hides_the_unanswered_line() -> None:
    text = exchange_text(
        exchange(1, 3, follow_up="Et ensuite ?"), with_note=False, pending_follow_up=True
    )
    assert "Follow-up: Et ensuite ?" in text and "(no answer)" not in text


def test_unrated_exchange_is_never_the_weakest_when_a_rated_one_exists() -> None:
    exchanges = [exchange(0, 3, unrated=True), exchange(1, 4)]
    assert weakest_index(exchanges) == 1
    assert "unscored" in exchange_text(exchanges[0])
