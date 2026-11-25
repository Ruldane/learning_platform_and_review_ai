"""Preuve 10b sur les graphes et le runner existants, sans transport MCP ni fournisseur réel."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.types import interrupt

from app.providers.llm.base import Tier
from tests.agents.graphs.council_models import URLS, CouncilModels, default_reply, prompt_text
from tests.agents.graphs.council_support import Council, MakeCouncil
from tests.agents.graphs.program_support import GOOD_PLAN, Builder, MakeBuilder
from tests.agents.graphs.web_support import SCORE_82
from tests.agents.runtime.runner_helpers import get_session, wait_idle


class InterruptChat(BaseChatModel):
    """Adaptateur expérimental. Le champ question transporte le prompt dans ce test local."""

    agent: str

    @property
    def _llm_type(self) -> str:
        return "mcp"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise AssertionError("Les graphes appellent le modèle en asynchrone.")

    async def _agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        answer = interrupt(
            {
                "kind": "model_call",
                "question": prompt_text(messages),
                "fields": [{"id": "role", "label": self.agent}],
            }
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])


class PlayedModels(CouncilModels):
    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        return InterruptChat(
            agent=agent or "", metadata={"tremplin_provider": "mcp", "tremplin_model": "codex"}
        )


async def _pending(run: Builder | Council) -> dict[str, Any]:
    await wait_idle(run.runner, run.sid)
    factory = run.web.factory if isinstance(run, Council) else run.factory
    row = await get_session(factory, run.user_id, run.sid)
    assert row.status == "waiting_user", (row.status, row.error)
    assert row.pending_interrupt
    return row.pending_interrupt


async def _brief(run: Builder | Council) -> str:
    pending = await _pending(run)
    assert pending["kind"] == "model_call"
    return str(pending["question"])


async def test_builder_retries_and_keeps_human_validation(make_builder_runner: MakeBuilder) -> None:
    control = await make_builder_runner()
    await control.wait_question()
    run = await make_builder_runner(models=PlayedModels())
    assert await _brief(run) == control.prompt_of_call(1)
    await run.resume("{}")
    assert "Your previous reply is invalid" in await _brief(run)
    await run.resume(GOOD_PLAN)
    assert (await _pending(run))["kind"] == "validate_program"
    assert len(await run.events("artifact.ready")) == 1
    await run.resume("validate")
    assert (await run.wait_status("completed")).cost_usd == 0


async def test_council_records_each_verdict_for_its_own_page(
    make_council_runner: MakeCouncil,
) -> None:
    run = await make_council_runner(models=PlayedModels())
    assert "Prepare the framing questions." in await _brief(run)
    await run.resume('{"questions":[]}')
    assert (await _pending(run))["kind"] == "framing"
    await run.resume("go")
    assert "Prepare the search queries." in await _brief(run)
    await run.resume('{"queries":[{"text":"ai product engineer","lang":"fr"}]}')
    for index, url in enumerate(URLS[:2]):
        prompt = await _brief(run)
        if index == 1:
            await run.runner.shutdown()
            run = await make_council_runner(sid=run.sid, models=PlayedModels())
            assert await _brief(run) == prompt
        assert url in prompt and "Score this source." in prompt
        assert '<<<UNTRUSTED_CONTENT source="page ' in prompt
        reply = {**json.loads(SCORE_82), "reason": f"Verdict de la page {index}."}
        await run.resume(json.dumps(reply))
    await wait_idle(run.runner, run.sid)
    found = [e for e in await run.events("source.found") if e["verdict"]]
    ids = {e["url"]: e["source_id"] for e in found}
    saved = await run.web.gateway.verdicts(run.user_id, run.sid, list(ids.values()))
    assert saved[ids[URLS[0]]].reason == "Verdict de la page 0."
    assert saved[ids[URLS[1]]].reason == "Verdict de la page 1."

    for _ in range(60):
        pending = await _pending(run)
        if pending["kind"] == "choose_path":
            break
        assert pending["kind"] == "model_call"
        await run.resume(default_reply(pending["fields"][0]["label"], pending["question"]))
    else:
        raise AssertionError("Le Conseil n’a pas atteint le choix du parcours.")
    proposals = await run.events("proposal.ready")
    assert len(proposals) == 2 and run.store.programs_started == 0
    await run.resume({"action": "choose", "proposal_ids": [proposals[0]["proposal_id"]]})
    assert (await run.wait_status("completed")).cost_usd == 0
    assert run.store.programs_started == 1
