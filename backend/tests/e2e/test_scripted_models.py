"""Modèles scriptés du parcours de bout en bout : une file de réponses par agent."""

from collections.abc import Sequence

import pytest
from langchain_core.messages import BaseMessage, HumanMessage

from app.agents.runtime.invoke import message_text
from tests.e2e.scripted_models import ScriptedModels


def _echo(messages: Sequence[BaseMessage]) -> str:
    return f"vu : {message_text(messages[-1])}"


async def test_scripted_models_serve_each_agent_in_order() -> None:
    models = ScriptedModels({"moderator": ["un", _echo], "scout": ["plan"]})
    moderator = await models.get_chat_model("u1", "standard", agent="moderator")
    scout = await models.get_chat_model("u1", "rapide", agent="scout")

    first = await moderator.ainvoke([HumanMessage("question")])
    plan = await scout.ainvoke([HumanMessage("cherche")])
    second = await moderator.ainvoke([HumanMessage("secret de January")])

    assert (first.content, plan.content) == ("un", "plan")
    assert second.content == "vu : secret de January"
    assert first.id != second.id  # un id par réponse : les bulles du débat ne se confondent pas
    assert models.served == {"moderator": 2, "scout": 1}
    assert models.remaining() == {}


async def test_streamed_call_takes_one_reply() -> None:
    models = ScriptedModels({"writer": ["# Titre\n\nCorps de la leçon.", "suite"]})
    writer = await models.get_chat_model("u1", "fort", agent="writer")

    chunks = [chunk async for chunk in writer.astream([HumanMessage("Écris la leçon.")])]

    assert "".join(str(c.content) for c in chunks) == "# Titre\n\nCorps de la leçon."
    assert len({c.id for c in chunks}) == 1
    assert models.served == {"writer": 1}


async def test_exhausted_queue_names_the_agent_not_the_messages() -> None:
    models = ScriptedModels({"skeptic": ["Objection : non."]})
    skeptic = await models.get_chat_model("u1", "standard", agent="skeptic")
    await skeptic.ainvoke([HumanMessage("tour 1")])

    with pytest.raises(RuntimeError) as caught:
        await skeptic.ainvoke([HumanMessage("message privé de January")])

    assert "skeptic" in str(caught.value)
    assert "privé" not in str(caught.value)


async def test_unknown_agent_has_an_empty_queue() -> None:
    models = ScriptedModels({})
    archivist = await models.get_chat_model("u1", "rapide", agent="archivist")

    with pytest.raises(RuntimeError, match="archivist"):
        await archivist.ainvoke([HumanMessage("x")])


async def test_delay_applies_to_the_listed_agents_only() -> None:
    models = ScriptedModels({"strategist": ["a"], "scribe": ["b"]}, delays={"strategist": 0.05})
    strategist = await models.get_chat_model("u1", "fort", agent="strategist")
    scribe = await models.get_chat_model("u1", "rapide", agent="scribe")

    assert (await scribe.ainvoke([HumanMessage("x")])).content == "b"
    assert (await strategist.ainvoke([HumanMessage("x")])).content == "a"
