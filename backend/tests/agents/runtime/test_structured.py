import json
import logging
from typing import Any

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agents.nodes.moderator_rounds import RoundPlan, RoundReview
from app.agents.nodes.scout.models import SourceScore
from app.agents.runtime.structured import extract_json_object, structured_call
from app.core.errors import AppError
from tests.agents.runtime.fakes import FlakyModel, fake_model

pytestmark = pytest.mark.usefixtures("emitted")
ARGS: dict[str, Any] = {"agent": "a", "step": "s", "intent": "i"}


class Title(BaseModel):
    title: str


async def test_structured_call_retries_then_succeeds() -> None:
    model, provider = fake_model(["pas du json", '{"title": 3}', '{"title": "Plan"}'])
    result = await structured_call(model, Title, [HumanMessage("x")], **ARGS)
    assert result.title == "Plan"
    # Le schéma est demandé, puis la réponse fautive et l'erreur sont renvoyées au modèle.
    first, second, third = provider.received
    assert '"title"' in str(first[-1].content) and "JSON" in str(first[-1].content)
    assert "pas du json" in str(second[-2].content)
    assert "title" in str(third[-1].content) and "valid string" in str(third[-1].content)


async def test_structured_call_fails_after_three_attempts() -> None:
    model, provider = fake_model(["x", "y", "z"])
    with pytest.raises(AppError) as e:
        await structured_call(model, Title, [HumanMessage("x")], **{**ARGS, "agent": "demo"})
    assert e.value.code == "structured_output_invalid"
    assert e.value.message == "La réponse de l'agent demo n'a pas le format attendu après 3 essais."
    assert len(provider.received) == 3


async def test_structured_call_retries_zero_means_one_attempt() -> None:
    model, provider = fake_model(["x", '{"title": "ok"}'])
    with pytest.raises(AppError):
        await structured_call(model, Title, [HumanMessage("x")], retries=0, **ARGS)
    assert len(provider.received) == 1


async def test_structured_call_treats_empty_content_as_retryable() -> None:
    # GLM : réflexion seule, `content` vide.
    model, _ = fake_model(["", "   ", '{"title": "Plan"}'])
    assert (await structured_call(model, Title, [HumanMessage("x")], **ARGS)).title == "Plan"


async def test_structured_call_accepts_json_in_a_fence_or_after_chatter() -> None:
    model, _ = fake_model(['Voici :\n```json\n{"title": "Plan"}\n```\nBonne lecture {ok}'])
    assert (await structured_call(model, Title, [HumanMessage("x")], **ARGS)).title == "Plan"


async def test_structured_call_final_error_details_carry_no_received_value() -> None:
    model, _ = fake_model(['{"title": 1}'] * 3)
    with pytest.raises(AppError) as e:
        await structured_call(model, Title, [HumanMessage("x")], **ARGS)
    assert e.value.details == {"agent": "a", "attempts": 3}


async def test_structured_call_emits_one_started_event(emitted: list[dict[str, Any]]) -> None:
    model, _ = fake_model(["x", '{"title": "ok"}'])
    await structured_call(model, Title, [HumanMessage("x")], **ARGS)
    assert [e["__tremplin_event__"] for e in emitted] == ["agent.started"]


async def test_structured_call_propagates_non_transient_errors() -> None:
    model = FlakyModel(fail_times=1, exc=ValueError("x"))
    with pytest.raises(ValueError):
        await structured_call(model, Title, [HumanMessage("x")], **ARGS)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('avant {"a": {"b": [1, 2]}} après', {"a": {"b": [1, 2]}}),
        ('{pas json} puis {"a": 2}', {"a": 2}),
        ('["liste"]', None),
        ("rien", None),
    ],
)
def test_extract_json_object(text: str, expected: dict[str, Any] | None) -> None:
    assert extract_json_object(text) == expected


async def test_structured_call_logs_each_failed_attempt_without_any_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="app")
    model, _ = fake_model(["pas du json secret", '{"title": 31415}', '{"title": "Plan"}'])
    await structured_call(model, Title, [HumanMessage("x")], **{**ARGS, "agent": "moderator"})
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert all("moderator" in w and "étape s" in w for w in warnings)
    assert "essai 1/3" in warnings[0] and "aucun objet JSON" in warnings[0]
    assert "essai 2/3" in warnings[1] and "title : Input should be a valid string" in warnings[1]
    assert "secret" not in caplog.text and "31415" not in caplog.text


def _summary(chars: int) -> str:
    """Résumé neutre en phrases françaises, de `chars` caractères exactement."""
    sentence = "Le Conseil converge vers un projet guidé dès la semaine 1, avec un test de recul. "
    return (sentence * (chars // len(sentence) + 1))[:chars]


async def test_round_review_with_the_too_long_summary_seen_from_glm_passes_first_time() -> None:
    # Réponse type relevée en réel (GLM 5.3 flash, bilan du tour 2) : `summary` de 536 caractères
    # pour un plafond de 400 ; neuf essais sur dix dépassaient (diagnostic D97).
    summary = _summary(536)
    model, provider = fake_model([json.dumps({"stable": True, "summary": summary})])
    review = await structured_call(model, RoundReview, [HumanMessage("x")], **ARGS)
    assert review.stable is True
    assert 0 < len(review.summary) <= 400 and summary.startswith(review.summary.rstrip("…"))
    assert len(provider.received) == 1


async def test_source_score_with_the_too_long_texts_seen_from_glm_passes_first_time() -> None:
    # Réponse type relevée en réel : `reason` de 302 caractères (plafond 300), `summary` de 701
    # (plafond 600), notes dans le barème.
    reply = {
        "authority": 12,
        "freshness": 17,
        "depth": 14,
        "author": 5,
        "pedagogy": 13,
        "reason": _summary(302),
        "summary": _summary(701),
    }
    model, provider = fake_model([json.dumps(reply)])
    score = await structured_call(model, SourceScore, [HumanMessage("x")], **ARGS)
    assert score.total == 61
    assert len(score.reason) <= 300 and len(score.summary) <= 600
    assert len(provider.received) == 1


async def test_round_plan_out_of_schema_is_still_refused() -> None:
    # Raccourcir ne vaut que pour le texte libre : un ordre de parole faux est toujours refusé.
    bad = json.dumps({"order": ["skeptic", "skeptic", "scout", "strategist"], "intent": "Q ?"})
    model, provider = fake_model([bad] * 3)
    with pytest.raises(AppError):
        await structured_call(model, RoundPlan, [HumanMessage("x")], **ARGS)
    assert len(provider.received) == 3
