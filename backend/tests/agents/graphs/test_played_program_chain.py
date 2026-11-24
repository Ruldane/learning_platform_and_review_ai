"""Rejoue le Conseil et le Constructeur avec le fournisseur effectivement livré."""

import json
from typing import Any

import pytest

from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT, PlayContext
from tests.agents.graphs.council_models import URLS, default_reply
from tests.agents.graphs.council_support import Council, MakeCouncil
from tests.agents.graphs.program_support import GOOD_PLAN, Builder, MakeBuilder
from tests.agents.runtime.runner_helpers import get_session, wait_idle


async def pending(run: Builder | Council) -> dict[str, Any]:
    await wait_idle(run.runner, run.sid)
    factory = run.web.factory if isinstance(run, Council) else run.factory
    row = await get_session(factory, run.user_id, run.sid)
    assert row.played_by == "codex" and row.cost_usd == 0
    assert row.status == "waiting_user" and row.pending_interrupt, (row.status, row.error)
    return row.pending_interrupt


def prompt(brief: dict[str, Any]) -> str:
    return "\n".join(message["content"] for message in brief["messages"])


async def submit(run: Builder | Council, brief: dict[str, Any], reply: str) -> None:
    await run.runner.submit_step(run.user_id, run.sid, brief["step_id"], reply)


def council_answer(brief: dict[str, Any], text: str) -> str:
    schema = (brief["output_schema"] or {}).get("title")
    if schema == "SearchSources":
        return json.dumps({"sources": [{"url": url, "title": "Documentation"} for url in URLS]})
    if schema == "ReadSource":
        return json.dumps({"text": "Texte de la page.", "title": "Documentation"})
    return default_reply(brief["agent"], text)


async def test_builder_from_brief_to_approved_program(
    make_builder_runner: MakeBuilder, user_id: str
) -> None:
    control = await make_builder_runner()
    await control.wait_question()
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "codex"))
    try:
        run = await make_builder_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    first = (await pending(run))["brief"]
    assert prompt(first) == control.prompt_of_call(1)
    with pytest.raises(AppError, match="Invalid reply"):
        await submit(run, first, "{}")
    retry = (await pending(run))["brief"]
    assert "Your previous reply is invalid" in prompt(retry)
    await submit(run, retry, GOOD_PLAN)
    assert (await pending(run))["kind"] == "validate_program"
    assert len(await run.events("artifact.ready")) == 1
    await run.resume("validate")
    assert (await run.wait_status("completed")).cost_usd == 0


@pytest.mark.parametrize("skip_during_speech", [False, True])
async def test_council_from_brief_to_chosen_proposal(
    make_council_runner: MakeCouncil, user_id: str, skip_during_speech: bool
) -> None:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "codex"))
    try:
        run = await make_council_runner()
    finally:
        PLAY_CONTEXT.reset(flag)
    sent_command = False
    for _ in range(60):
        current = await pending(run)
        if current["kind"] == "framing":
            await run.resume("go")
        elif current["kind"] == "choose_path":
            break
        else:
            brief = current["brief"]
            text = prompt(brief)
            if (
                skip_during_speech
                and not sent_command
                and "Current round: 2\n" in text
                and "À toi de parler." in text
            ):
                await run.post_message("", "to_proposals")
                sent_command = True
            await submit(run, brief, council_answer(brief, text))
    else:
        pytest.fail("Le Conseil n'a pas atteint le choix humain.")
    proposals = await run.events("proposal.ready")
    assert len(proposals) == 2 and run.store.programs_started == 0
    if skip_during_speech:
        assert sent_command
        speeches = await run.agent_messages(step_prefix="tour-2")
        assert len(speeches) == 1, (
            "La prise de parole en cours doit arriver avant les propositions."
        )
    await run.resume({"action": "choose", "proposal_ids": [proposals[0]["proposal_id"]]})
    assert (await run.wait_status("completed")).cost_usd == 0
    assert run.store.programs_started == 1
