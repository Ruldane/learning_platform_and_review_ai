"""Parcours `study_session` (D102) : le Tuteur mène la séance (sections, exercice, trois questions
finales, fin), « Terminer » à n'importe quelle question, reprise après un arrêt du back sans
seconde écriture, tableau sans échec, contexte mémoire, journaux sans contenu."""

import logging

import pytest

from app.agents.nodes.mermaid_rules import mermaid_problems
from app.agents.nodes.tutor.answers import CHECK_REQUEST
from app.agents.nodes.tutor.models import TeachTurn
from app.agents.nodes.tutor.teach import (
    FINAL_REQUEST,
    MAX_MERMAID_CHARS,
    NO_MEMORY_CONTEXT,
    TEACH_REQUEST,
)
from app.agents.nodes.tutor.wrap import SUMMARY_REQUEST
from app.agents.tools.memory_port import NO_MEMORY
from app.agents.tools.study_port import StudyOutcome
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.quiz_support import between_untrusted_markers
from tests.agents.graphs.study_support import MakeStudy, StudyRun, teach_turn
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.study import EXERCISE, MEMORY_MARK, MODULE, SOLUTION, STUDY_ID

TQ, FS = "tutor_question", "finish_session"
QUESTIONS = 2 + 1 + 3  # deux sections, l'exercice, trois questions finales
LONG_VALID = "flowchart TD\n" + "\n".join(
    f'N{n}["{"a" * 60}"] --> N{n + 1}["b"]' for n in range(30)
)


async def _finish(run: StudyRun) -> StudyOutcome:
    await run.wait_question(FS)
    await run.resume("finish")
    await run.wait_status("completed")
    assert run.store.finished is not None
    return run.store.finished


async def test_session_walks_sections_exercise_and_final(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner()
    await run.answer_all(QUESTIONS)
    outcome = await _finish(run)
    assert await run.kinds() == [TQ] * QUESTIONS + [FS]
    assert [(o.phase, o.index) for o in outcome.outcomes] == [
        ("section", 0),
        ("section", 1),
        ("exercise", 0),
        ("final", 0),
        ("final", 1),
        ("final", 2),
    ]
    assert all(o.verdict == "correct" and o.hints == 0 for o in outcome.outcomes)
    assert outcome.exercise_done and not outcome.ended_early
    assert outcome.summary == "Bonne séance : la softmax est acquise."
    assert len(run.prompts(FINAL_REQUEST)) == 1  # les questions finales, écrites une fois
    said = await run.events("agent.message")
    assert said[0]["text"].startswith(f"On travaille « {MODULE} »")
    assert said[1]["citations"][0]["index"] == 1  # « [1] » du message de la section
    assert "Temps enregistré : 42 min." in said[-1]["text"]
    assert "Acquis mis à jour : Attention (En cours)." in said[-1]["text"]
    done = (await run.events("run.completed"))[0]["summary"]
    assert done == f"Session d'étude terminée : « {MODULE} », 42 min."


async def test_exercise_expected_is_lesson_solution(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner()
    await run.answer_all(2)
    exercise = await run.wait_question()
    assert exercise["question"] == EXERCISE
    await run.answer("Environ 0,27 et 0,73.")
    await run.wait_question()  # première question finale
    check = run.prompts(CHECK_REQUEST)[-1]
    assert SOLUTION in between_untrusted_markers(check, "question")
    await run.resume({"action": "finish"})
    await run.wait_status("completed")
    assert run.store.finished is not None
    assert run.store.finished.outcomes[2].expected == SOLUTION
    assert not any(SOLUTION in p for p in run.prompts(TEACH_REQUEST))  # jamais réécrit


async def test_finish_at_any_question_jumps_to_summary(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner()
    await run.answer_all(1)
    await run.wait_question()
    await run.resume({"action": "finish"})
    await run.wait_status("completed")
    outcome = run.store.finished
    assert outcome is not None and outcome.ended_early and not outcome.exercise_done
    assert [o.phase for o in outcome.outcomes] == ["section"]
    assert await run.kinds() == [TQ, TQ]
    assert "January a terminé la séance avant" in run.prompts(SUMMARY_REQUEST)[0]


async def test_replay_at_question_keeps_question(make_study_runner: MakeStudy) -> None:
    first = await make_study_runner()
    asked = await first.wait_question()
    await first.runner.shutdown()
    second = await make_study_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == []  # en attente : rien à relancer
    await second.answer("La softmax normalise.")
    again = await second.wait_question()
    assert again["question"] == "Que fait la softmax des scores ?"
    check = second.prompts(CHECK_REQUEST)[0]
    assert asked["question"] in between_untrusted_markers(check, "question")
    assert len(first.prompts(TEACH_REQUEST)) == 1 and len(second.prompts(TEACH_REQUEST)) == 1


async def test_replay_of_wrap_up_finishes_once(make_study_runner: MakeStudy) -> None:
    # Arrêt du back juste après l'écriture de la fin : `wrap_up` rejoué relit la fin rangée.
    first = await make_study_runner()
    first.store.block_after_finish = True
    await first.answer_all(QUESTIONS)
    await first.wait_question(FS)
    await first.resume("finish")
    await wait_until(lambda: first.store.finish_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_finish = False
    second = await make_study_runner(sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert second.store.finish_calls == 2
    assert second.prompts(SUMMARY_REQUEST) == []  # le bilan n'est pas redemandé
    assert len(await second.events("run.completed")) == 1


@pytest.mark.parametrize(
    ("mermaid", "drawn"),
    [
        ('flowchart TD\nA["Scores"] --> B["Poids"]', True),
        ("graph XY ((( pas du Mermaid", False),
        (LONG_VALID, False),  # valable pour la grammaire, plus long que le plafond : retiré
    ],
)
async def test_bad_mermaid_is_dropped_not_failed(
    make_study_runner: MakeStudy, mermaid: str, drawn: bool
) -> None:
    models = CouncilModels()
    models.when("tutor", TEACH_REQUEST, teach_turn(mermaid=mermaid))
    run = await make_study_runner(models)
    await run.wait_question()
    boards = await run.events("board.update")
    if drawn:
        assert boards == [
            {
                "mermaid": boards[0]["mermaid"],
                "step": 1,
                "board_id": None,
                "kind": None,
                "title": "L'essentiel en 5 lignes",
            }
        ]
        assert "Scores" in boards[0]["mermaid"]
    else:
        assert boards == []


def test_tutor_mermaid_has_no_schema_cap() -> None:
    turn = TeachTurn.model_validate_json(teach_turn(mermaid="x" * (MAX_MERMAID_CHARS + 500)))
    assert turn.mermaid is not None  # refusé par le schéma, l'étape échouerait (D102)
    assert mermaid_problems(LONG_VALID) == [] and len(LONG_VALID) > MAX_MERMAID_CHARS


async def test_tutor_prompt_has_memory_context(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner()
    await run.wait_question()
    [teach] = run.prompts(TEACH_REQUEST)
    assert MEMORY_MARK in teach and "Python" in teach
    tools = [e["tool"] for e in await run.events("tool.called")]
    assert tools == ["memory_get_skills", "memory_search", "memory_search"]
    assert MODULE in [e["args"].get("query") for e in await run.events("tool.called")]


async def test_memory_unavailable_does_not_stop_the_session(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner(memory=NO_MEMORY)
    await run.wait_question()
    assert NO_MEMORY_CONTEXT in run.prompts(TEACH_REQUEST)[0]


async def test_unknown_study_session_fails_readably(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner(start=False)
    run.sid = await run.runner.start(run.user_id, "study_session", {"study_session_id": "x" * 36})
    failed = await run.wait_status("failed")
    assert failed.error is not None and failed.error["code"] == "study_session_not_found"


async def test_logs_carry_ids_only(
    make_study_runner: MakeStudy, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    run = await make_study_runner()
    secret = "Mon secret de réponse"
    await run.answer_all(QUESTIONS, text=secret)
    await _finish(run)
    text = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app."))
    assert STUDY_ID in text
    assert all(s not in text for s in (secret, "softmax", MODULE, SOLUTION, "Bonne séance"))
