"""Parcours `interview` (D145, tour 1) : un débrief qui échoue ne fait pas perdre les réponses ;
un modèle muet à un tour se voit (réponse « non notée ») sans écraser une note déjà donnée."""

import pytest

from app.agents.nodes.interviewer import debrief as debrief_module
from app.agents.nodes.interviewer.debrief import DEBRIEF_REQUEST
from app.agents.nodes.interviewer.turn import TURN_REQUEST
from app.agents.runtime.costs import TokenBudgetExceeded
from tests.agents.graphs.interview_support import (
    MakeInterview,
    debrief_json,
    expected,
    interviewer,
    prompts,
    question_text,
    turn_json,
)
from tests.support.interviews import FakeInterviewStore

FOLLOW_UP = "Peux-tu préciser le résultat obtenu ?"
UNREADABLE = ["pas du json"] * 3  # les trois essais d'un appel structuré


async def test_debrief_failure_keeps_the_answers(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    run = await interview_runner(interviewer(debriefs=UNREADABLE))
    await run.answer_all(4)
    await run.wait_status("completed")
    saved = interview_store.only
    assert [e.index for e in saved.exchanges] == [0, 1, 2, 3]
    assert (saved.debrief, saved.flags, saved.cards) == (None, [], [])
    assert len(prompts(run.models, DEBRIEF_REQUEST)) == 3
    [done] = await run.events("run.completed")
    assert "Your answers are saved" in done["summary"] and "debrief" in done["summary"]


async def test_debrief_timeout_keeps_the_answers(
    interview_runner: MakeInterview,
    interview_store: FakeInterviewStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(debrief_module, "DEBRIEF_CALL_TIMEOUT_S", 0.3)
    models = interviewer()
    models.block = lambda agent, prompt: DEBRIEF_REQUEST in prompt
    run = await interview_runner(models)
    await run.answer_all(4)
    await run.wait_status("completed")
    saved = interview_store.only
    assert len(saved.exchanges) == 4 and saved.debrief is None


async def test_token_cap_still_fails_the_session(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    models = interviewer()

    async def cap(agent: str, prompt: str) -> None:
        if DEBRIEF_REQUEST in prompt:
            raise TokenBudgetExceeded(1000)

    models.hooks.append(cap)
    run = await interview_runner(models)
    await run.answer_all(4)
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "token_cap_reached"
    assert interview_store.save_calls == 0


async def test_fallback_note_does_not_overwrite_the_first_answer_note(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    turns = [turn_json(1, FOLLOW_UP), *UNREADABLE]  # la réponse à la relance n'est pas lisible
    debriefs = [debrief_json(expected=expected(0))]
    run = await interview_runner(interviewer(turns=turns, debriefs=debriefs))
    await run.answer_all(5)
    await run.wait_status("completed")
    saved = interview_store.only
    assert (saved.exchanges[0].note, saved.exchanges[0].unrated) == (1, False)
    assert saved.debrief is not None and saved.debrief.missed == [0]
    assert [c.front for c in saved.cards] == [question_text(1)]


async def test_unrated_answer_is_visible(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    run = await interview_runner(interviewer(turns=UNREADABLE))
    await run.answer_all(4)
    await run.wait_status("completed")
    saved = interview_store.only
    assert [e.unrated for e in saved.exchanges] == [True, False, False, False]
    assert saved.debrief is not None and saved.debrief.unrated == [0]
    [debrief_prompt] = prompts(run.models, DEBRIEF_REQUEST)
    assert "unscored" in debrief_prompt
    [done] = await run.events("run.completed")
    assert "1 answer could not be scored" in done["summary"]


async def test_final_turn_prompt_does_not_say_the_follow_up_is_unanswered(
    interview_runner: MakeInterview,
) -> None:
    run = await interview_runner(interviewer(turns=[turn_json(3, FOLLOW_UP)] * 30))
    await run.answer_all(2)
    await run.question()
    first, second = prompts(run.models, TURN_REQUEST)
    assert "(pas de réponse)" not in first + second and FOLLOW_UP in second


async def test_duplicate_expected_points_are_kept_once(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    turns = [turn_json(4), turn_json(1), turn_json(4), turn_json(4)]
    debriefs = [debrief_json(expected=[*expected(1), *expected(1)])]
    run = await interview_runner(interviewer(turns=turns, debriefs=debriefs))
    await run.answer_all(4)
    await run.wait_status("completed")
    saved = interview_store.only
    assert saved.debrief is not None
    assert [e.index for e in saved.debrief.expected] == [1] and len(saved.cards) == 1
