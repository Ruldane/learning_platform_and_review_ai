from typing import Any

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

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
