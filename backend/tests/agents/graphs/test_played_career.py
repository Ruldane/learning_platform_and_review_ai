"""Parcours carrière joués avec le fournisseur de production et les ports métier de test."""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.agents.tools.committee_schema import PERSONAS, speaking_order
from app.core.played import PLAY_CONTEXT, PlayContext
from app.db.models.agents import LlmCall
from tests.agents.graphs.capture_support import PAGE_TEXT, MakeCapture
from tests.agents.graphs.committee_support import MakeCommittee
from tests.agents.graphs.design_support import MakeDesign
from tests.agents.graphs.gap_support import MakeGap
from tests.agents.graphs.intake_support import MakeIntake, field_values
from tests.agents.graphs.interview_support import MakeInterview, answer
from tests.agents.graphs.kit_support import MakeKit
from tests.agents.graphs.radar_support import MakeRadar, analyst, batch, postings
from tests.agents.graphs.review_support import MakeReview
from tests.agents.runtime.runner_helpers import get_session, wait_idle
from tests.support.capture import SUMMARY
from tests.support.gap import POSTING_ID


async def start[T](user_id: str, launch: Awaitable[T]) -> T:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "codex"))
    try:
        return await launch
    finally:
        PLAY_CONTEXT.reset(flag)


async def play(run: Any, human_answer: Callable[[dict[str, Any]], Any] | None = None) -> list[str]:
    roles: list[str] = []
    for _ in range(50):
        await wait_idle(run.runner, run.sid)
        row = await get_session(run.factory, run.user_id, run.sid)
        assert row.played_by == "codex" and row.cost_usd == 0
        if row.status == "completed":
            break
        pending = row.pending_interrupt
        assert pending is not None, (row.status, row.error)
        if pending["kind"] != "mcp_model":
            assert human_answer is not None, pending["kind"]
            await run.runner.resume(
                run.user_id, run.sid, pending["interrupt_id"], human_answer(pending)
            )
            continue
        brief = pending["brief"]
        roles.append(brief["agent"])
        messages = [HumanMessage(m["content"]) for m in brief["messages"]]
        _, response, _ = run.models.reply(brief["agent"], messages)
        await run.runner.submit_step(run.user_id, run.sid, brief["step_id"], response)
    else:
        raise AssertionError("Le parcours n'a pas abouti.")
    async with run.factory() as db:
        calls = (await db.scalars(select(LlmCall).where(LlmCall.session_id == run.sid))).all()
        assert len(calls) == len(roles) == len(run.models.calls)
        assert all((c.provider, c.model, c.cost_usd) == ("mcp", "codex", 0) for c in calls)
    return roles


async def test_played_capture(make_capture_runner: MakeCapture, user_id: str) -> None:
    run = await start(user_id, make_capture_runner(body={"text": PAGE_TEXT}))
    assert await play(run) == ["archivist"]
    assert run.store.store_calls[0].digest.summary == SUMMARY


async def test_played_gap(gap_runner: MakeGap, user_id: str) -> None:
    run = await start(user_id, gap_runner())
    assert await play(run) == ["analyst", "analyst"]
    assert run.store.gaps[POSTING_ID].score == 62


async def test_played_review(review_runner: MakeReview, user_id: str) -> None:
    run = await start(user_id, review_runner())
    roles = await play(run, lambda _: {"choice": "finish"})
    assert {"ats_reader", "recruiter", "scout"} <= set(roles)
    assert run.store.saved_refs == ["a1", "a2", "r1"] and len(run.store.closed) == 1


async def test_played_design_renders_two_passes_and_waits_for_validation(
    design_runner: MakeDesign, user_id: str
) -> None:
    run = await start(user_id, design_runner())
    run.store.scores = [72, 88]
    decisions = []

    def confirm(question: dict[str, Any]) -> str:
        decisions.append(question["kind"])
        assert run.store.rendered == [1, 2]
        assert not run.store.finished
        return "validate"

    assert await play(run, confirm) == ["designer"] * 3
    assert decisions == ["cv_template"]
    assert list(run.store.finished.values()) == [("ready", None)]


async def test_played_intake(intake_runner: MakeIntake, user_id: str) -> None:
    run = await start(user_id, intake_runner())

    def confirm(question: dict[str, Any]) -> dict[str, Any]:
        assert not run.store.saved
        return {"choice": "create", "fields": field_values(question)}

    assert await play(run, confirm) == ["tracker"]
    assert run.store.created[run.sid]


async def test_played_kit(kit_runner: MakeKit, user_id: str) -> None:
    run = await start(user_id, kit_runner())
    assert {"tracker", "scout"} == set(await play(run))
    assert len(run.store.rows) == 7 and all(r.status == "ready" for r in run.store.rows.values())


async def test_played_interview(interview_runner: MakeInterview, user_id: str) -> None:
    run = await start(user_id, interview_runner())
    assert await play(run, lambda _: answer()) == ["interviewer"] * 6
    assert run.store.only.debrief is not None and len(run.store.only.exchanges) == 4


async def test_played_committee(committee_runner: MakeCommittee, user_id: str) -> None:
    run = await start(user_id, committee_runner())
    roles = await play(run)
    assert roles == [*PERSONAS, *speaking_order(1), *speaking_order(2), *PERSONAS, "moderator"]
    assert [v.persona for v in run.store.only.votes] == list(PERSONAS)
    assert run.store.only.synthesis.verdict == "yes"


async def test_played_radar(radar_runner: MakeRadar, user_id: str) -> None:
    run = await start(user_id, radar_runner(analyst(batch(5), batch(2)), sources=postings(7)))
    assert await play(run) == ["analyst"] * 2
    assert run.store.summary and run.store.summary.analyzed == 7
