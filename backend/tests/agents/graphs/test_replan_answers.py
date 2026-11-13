"""Parcours `replan` (D106, relecture de 5.8 m3 et m4) : une note vide repose la question avec
une aide ; une acceptation périmée garde la note de January pour la proposition suivante ; un
programme terminé finit par un texte qui le dit (relecture 5.9, m4)."""

from app.agents.graphs.replan import ACCEPT_INTERRUPT, STALE_NOTE
from app.agents.nodes.strategist.replan_steps import EMPTY_NOTE_HINT, FINISHED_TEXT
from tests.agents.graphs.replan_support import MakeReplan, ReplanRun
from tests.support.replan import replan_context


async def _proposed(run: ReplanRun, option: str) -> None:
    await run.wait_question("replan_option")
    await run.resume(option)
    await run.wait_question()


async def test_empty_note_asks_again_with_hint(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(plan=replan_context("late_twice", late=1))
    await _proposed(run, "reduce_scope")
    await run.resume({"answers": {"note": "  "}})
    hinted = await run.wait_question()
    assert hinted["question"] == f"{EMPTY_NOTE_HINT} {ACCEPT_INTERRUPT['question']}"
    await run.resume("go")  # réponse invalide : la question revient, sans aide
    plain = await run.wait_question()
    assert plain["question"] == ACCEPT_INTERRUPT["question"]
    assert len(run.store.previews) == 1


async def test_stale_after_revision_keeps_note(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(
        plan=replan_context("late_twice", late=1),
        prepare=lambda s: setattr(s, "stale_applies", 1),
    )
    await _proposed(run, "reduce_scope")
    await run.resume({"answers": {"note": "Garde la pratique de l'API"}})
    await run.wait_question()
    await run.resume("accept")  # périmée : nouvelle proposition, la note reste (m4)
    await run.wait_question()
    assert [c.revision for c in run.store.previews] == [0, 1, 2]
    last = run.prompts()[-1]
    assert STALE_NOTE in last and "Garde la pratique de l'API" in last
    assert run.store.previews[2].reason.endswith(": Garde la pratique de l'API")


async def test_finished_program_ends_with_its_own_text(make_replan_runner: MakeReplan) -> None:
    run = await make_replan_runner(prepare=lambda s: setattr(s, "finished", True))
    await run.wait_status("completed")
    assert (await run.events("run.completed"))[0]["summary"] == FINISHED_TEXT
    assert (await run.said())[-1] == FINISHED_TEXT and await run.events("artifact.ready") == []
