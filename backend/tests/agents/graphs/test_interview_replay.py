"""Parcours `interview` (D145), reprises : un redémarrage pendant l'attente repose la même question
sans appeler le modèle, une réponse en double ne compte qu'une fois, le rangement est idempotent
par session, les journaux ne citent ni question, ni réponse, ni entreprise."""

import inspect
import logging

import pytest

from app.agents.nodes.interviewer.debrief import DEBRIEF_REQUEST
from app.agents.nodes.interviewer.plan import PLAN_REQUEST
from app.agents.nodes.interviewer.turn import TURN_REQUEST, ask
from app.core.errors import AppError
from tests.agents.graphs.interview_support import (
    MakeInterview,
    answer,
    interviewer,
    prompts,
    question_text,
    turn_json,
)
from tests.agents.runtime.runner_helpers import get_session, wait_until
from tests.support.interviews import COMPANY, FakeInterviewStore

FOLLOW_UP = "Peux-tu préciser le résultat obtenu ?"


async def test_interrupt_node_is_pure() -> None:
    assert list(inspect.signature(ask).parameters) == ["state"]  # ni port ni modèle


async def test_replay_at_question_keeps_question(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    """Le back redémarre pendant que la question attend : la même question attend, le plan n'est pas
    redemandé, rien n'est relu ni écrit, et la réponse est reçue par le nouveau processus."""
    first = await interview_runner()
    await first.answer_all(2)
    question = await first.question()
    await first.runner.shutdown()
    second = await interview_runner(interviewer(), sid=first.sid)
    assert await second.runner.recover_on_startup() == []  # `waiting_user` : rien à relancer
    row = await second.wait_status("waiting_user")
    assert row.pending_interrupt is not None
    assert row.pending_interrupt["interrupt_id"] == question["interrupt_id"]
    assert row.pending_interrupt["question"] == question["question"] == question_text(3)
    assert second.models.calls == [] and interview_store.save_calls == 0
    assert interview_store.context_calls == 1
    second.pending = row.pending_interrupt
    await second.answer(answer())
    assert (await second.question())["question"] == question_text(4)
    await second.answer(answer())
    await second.wait_status("completed")
    assert prompts(second.models, PLAN_REQUEST) == []  # jamais replanifié
    assert len(prompts(second.models, TURN_REQUEST)) == 2
    assert len(interview_store.only.exchanges) == 4


async def test_replay_at_follow_up_keeps_follow_up(interview_runner: MakeInterview) -> None:
    first = await interview_runner(interviewer(turns=[turn_json(3, FOLLOW_UP)]))
    await first.answer_all(1)
    question = await first.question()
    assert question["question"] == FOLLOW_UP
    await first.runner.shutdown()
    second = await interview_runner(interviewer(), sid=first.sid)
    row = await second.wait_status("waiting_user")
    assert row.pending_interrupt is not None and row.pending_interrupt["question"] == FOLLOW_UP
    assert second.models.calls == []


async def test_double_answer_counts_once(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    run = await interview_runner()
    question = await run.question()
    await run.runner.resume(run.user_id, run.sid, question["interrupt_id"], answer("Première."))
    with pytest.raises(AppError) as stale:  # la même question, une seconde fois
        await run.runner.resume(run.user_id, run.sid, question["interrupt_id"], answer("Seconde."))
    assert stale.value.status_code == 409
    await run.answer_all(3)
    await run.wait_status("completed")
    exchanges = interview_store.only.exchanges
    assert [(e.index, e.answer) for e in exchanges][:2] == [
        (0, "Première."),
        (1, "Ma réponse détaillée."),
    ]
    assert len(exchanges) == 4 and len(prompts(run.models, TURN_REQUEST)) == 4
    assert all("Seconde." not in c.prompt for c in run.models.calls)


async def test_save_is_idempotent(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    """Arrêt du back pendant le rangement : le nœud rejoué relit l'issue de la session, et le
    débrief n'est pas redemandé."""
    interview_store.block_after_save = True
    first = await interview_runner()
    await first.answer_all(4)
    await wait_until(lambda: interview_store.save_calls == 1)
    await first.runner.shutdown()
    interview_store.block_after_save = False
    second = await interview_runner(interviewer(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert interview_store.save_calls == 2 and len(interview_store.saved) == 1
    assert second.models.calls == []  # ni plan, ni tour, ni débrief redemandés
    assert len(prompts(first.models, DEBRIEF_REQUEST)) == 1
    assert len(interview_store.only.exchanges) == 4


async def test_store_refusal_fails_with_its_message(
    interview_runner: MakeInterview, interview_store: FakeInterviewStore
) -> None:
    async def refuse(*args: object, **kwargs: object) -> None:
        raise AppError("interview_not_found", "Entretien introuvable.", 404)

    interview_store.context = refuse  # type: ignore[method-assign]
    run = await interview_runner()
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "interview_not_found"


async def test_interview_text_never_logged(
    caplog: pytest.LogCaptureFixture, interview_runner: MakeInterview
) -> None:
    caplog.set_level(logging.INFO)  # pas le SQL d'aiosqlite, qui cite la ligne de la session
    caplog.set_level(logging.DEBUG, logger="app")
    secrets = ("Réponse ultra secrète", "Relance ultra secrète", COMPANY)
    run = await interview_runner(interviewer(turns=[turn_json(1, secrets[1])]))
    await run.question()
    await run.answer(answer(secrets[0]))
    await run.question()
    await run.answer(answer(secrets[0]))
    for _ in range(3):
        await run.question()
        await run.answer(answer(secrets[0]))
    await run.wait_status("completed")
    row = await get_session(run.factory, run.user_id, run.sid)
    assert row.status == "completed"
    for secret in (*secrets, question_text(1), question_text(2)):
        assert secret not in caplog.text
