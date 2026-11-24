"""Parcours `cv_review` (D129) : la question de sortie `cv_output` en boucle (rapport, PDF,
terminer), l'interruption seule dans son nœud, et le rejeu après un arrêt du back (Review Focus
n° 4) : la même question attend, aucune modification ni version en double."""

import inspect

from app.agents.nodes.review_output import CLOSED, ask_output, pages_text
from tests.agents.graphs.review_support import MakeReview, reviewers
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.cv_review import REVIEW_ID, FakeCvReviewStore


async def test_output_loop_report_then_pdf_then_finish(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    run = await review_runner()
    await run.question()
    await run.answer("report")
    await run.question()
    await run.answer({"choice": "pdf", "version_id": "v1"})
    await run.question()
    await run.answer({"choice": "finish"})
    await run.wait_status("completed")
    assert await run.events("artifact.ready") == [
        {
            "artifact_id": f"rapport-{REVIEW_ID}",
            "kind": "cv_report",
            "title": "CV review report",
            "url": f"/career/cv/reviews/{REVIEW_ID}#report",
        },
        {
            "artifact_id": "v1",
            "kind": "cv_pdf",
            "title": "Tailored CV (PDF)",
            "url": "/api/v1/cv/versions/v1/pdf",
        },
    ]
    assert review_store.rendered == ["v1"] and review_store.closed == [REVIEW_ID]
    [done] = await run.events("run.completed")
    assert done["summary"] == CLOSED


async def test_pages_exceeded_is_said_then_question_again(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    review_store.statuses["v2"] = "pages_exceeded"
    run = await review_runner()
    await run.question()
    await run.answer({"choice": "pdf", "version_id": "v2"})
    await run.question()
    assert (await run.said())[-1] == (
        "The tailored CV exceeds 1 page. Remove a line or allow one more page."
    )
    assert pages_text(2).startswith("The tailored CV exceeds 2 pages")
    assert await run.events("artifact.ready") == []


async def test_failed_render_is_said(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    review_store.statuses["v3"] = "failed"
    run = await review_runner()
    await run.question()
    await run.answer({"choice": "pdf", "version_id": "v3"})
    await run.question()
    assert (await run.said())[-1].startswith("The PDF could not be generated")


async def test_unknown_answer_asks_again_without_writing(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    run = await review_runner()
    first = await run.question()
    for value in ("pdf", {"choice": "pdf"}, "valider", {"choice": "autre"}):
        await run.answer(value)
        again = await run.question()
        assert again["interrupt_id"] != first["interrupt_id"] and again["kind"] == "cv_output"
        first = again
    assert review_store.render_calls == [] and review_store.closed == []


async def test_interrupt_node_has_no_write(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    assert list(inspect.signature(ask_output).parameters) == ["state"]  # ni port ni modèle
    run = await review_runner()
    await run.question()
    model_calls, saves = len(run.models.calls), review_store.save_calls
    await run.answer("report")
    await run.question()
    assert len(run.models.calls) == model_calls and review_store.save_calls == saves


async def test_replay_at_output_question_keeps_question(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    """Le back redémarre pendant que la question attend : la même question attend, rien n'est
    rejoué ni rangé deux fois, et la réponse est reçue par le nouveau processus."""
    first = await review_runner()
    question = await first.question()
    await first.runner.shutdown()
    second = await review_runner(reviewers(), sid=first.sid)
    assert await second.runner.recover_on_startup() == []  # `waiting_user` : rien à relancer
    row = await second.wait_status("waiting_user")
    assert row.pending_interrupt is not None
    assert row.pending_interrupt["kind"] == "cv_output"
    assert row.pending_interrupt["interrupt_id"] == question["interrupt_id"]
    assert review_store.save_calls == 1 and second.models.calls == []
    await second.answer("finish")
    await second.wait_status("completed")
    assert review_store.closed == [REVIEW_ID] and review_store.save_calls == 1


async def test_replay_after_save_writes_once(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    review_store.block_after_save = True
    first = await review_runner()
    await wait_until(lambda: review_store.save_calls == 1)
    await first.runner.shutdown()
    review_store.block_after_save = False
    second = await review_runner(reviewers(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.question()
    assert review_store.saved_refs == ["a1", "a2", "r1"] and review_store.save_calls == 2
    assert second.models.calls == []  # la confrontation n'est pas rejouée


async def test_replay_after_pdf_answer_renders_once(
    review_runner: MakeReview, review_store: FakeCvReviewStore
) -> None:
    review_store.block_after_render = True
    first = await review_runner()
    await first.question()
    await first.answer({"choice": "pdf", "version_id": "v1"})
    await wait_until(lambda: len(review_store.render_calls) == 1)
    await first.runner.shutdown()
    review_store.block_after_render = False
    second = await review_runner(reviewers(), sid=first.sid)
    second.pending = first.pending
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.question()
    assert review_store.render_calls == ["v1", "v1"] and review_store.rendered == ["v1"]
    [artifact] = await second.events("artifact.ready")
    assert artifact["kind"] == "cv_pdf"
