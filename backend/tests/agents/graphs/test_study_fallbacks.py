"""Le Tuteur sans réponse du modèle (contrôle 5.18, D115) : un appel qui ne répond jamais (ou
une panne passagère) ne fait plus échouer la séance. Chaque nœud se replie après son échéance
(réduite ici), sans second appel : réponse non corrigée (`skipped`), indice compté sans texte,
section telle qu'écrite, questions finales tirées de la leçon, message laissé sans réponse.

Avant le correctif, l'appel bloqué tenait jusqu'au plafond du nœud (120 s, `node_timeout`) : ces
tests restaient sans question nouvelle et échouaient."""

import pytest

from app.agents.nodes.tutor import fallback
from app.agents.nodes.tutor.answers import CHECK_REQUEST, HINT_REQUEST
from app.agents.nodes.tutor.fallback import (
    FALLBACK_FINAL_INTRO,
    NO_REPLY,
    UNCHECKED,
    final_questions_from_lesson,
)
from app.agents.nodes.tutor.teach import FINAL_REQUEST, REPLY_REQUEST, TEACH_REQUEST
from app.core.errors import AppError
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.study_support import MakeStudy, StudyRun
from tests.support.study import (
    MODULE,
    SECTION_TEXTS,
    FakeStudyStore,
    study_context,
)

QUESTIONS = 2 + 1 + 3  # deux sections, l'exercice, trois questions finales


@pytest.fixture(autouse=True)
def short_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fallback, "TUTOR_CALL_TIMEOUT_S", 0.05)


def _blocking(marker: str) -> CouncilModels:
    """Le Tuteur ne répond jamais aux demandes qui contiennent `marker`."""
    models = CouncilModels()
    models.block = lambda agent, prompt: agent == "tutor" and marker in prompt
    return models


async def _said(run: StudyRun) -> list[str]:
    return [e["text"] for e in await run.events("agent.message")]


async def _end(run: StudyRun, *, wait: bool = True) -> None:
    if wait:  # une question nouvelle (celle déjà lue ne compte pas)
        await run.wait_question()
    await run.resume({"action": "finish"})
    await run.wait_status("completed")


async def test_unanswered_check_counts_as_skipped_and_the_session_goes_on(
    make_study_runner: MakeStudy,
) -> None:
    run = await make_study_runner(_blocking(CHECK_REQUEST))
    await run.answer_all(QUESTIONS)
    await run.wait_question("finish_session")
    await run.resume("finish")
    await run.wait_status("completed")
    finished = run.store.finished
    assert finished is not None
    assert [o.verdict for o in finished.outcomes] == ["skipped"] * QUESTIONS
    assert not finished.exercise_done  # ni pratique cochée ni fiche (`skipped`, F13)
    assert run.models.blocked == QUESTIONS  # un seul appel par réponse, aucun nouvel essai
    assert (await _said(run)).count(UNCHECKED) == QUESTIONS


@pytest.mark.parametrize(
    ("code", "status"),
    [("structured_output_invalid", "completed"), ("llm_key_rejected", "failed")],
)
async def test_unreadable_check_falls_back_but_a_rejected_key_fails(
    make_study_runner: MakeStudy, code: str, status: str
) -> None:
    models = CouncilModels()

    async def refuse(agent: str, prompt: str) -> None:
        if CHECK_REQUEST in prompt:
            raise AppError(code, "Le modèle n'a pas répondu comme prévu.", 502)

    models.hooks.append(refuse)
    run = await make_study_runner(models)
    await run.answer_all(1)
    if status == "failed":
        row = await run.wait_status("failed")
        assert row.error is not None and row.error["code"] == code
        return
    await _end(run)
    assert run.store.finished is not None
    assert [o.verdict for o in run.store.finished.outcomes] == ["skipped"]


async def test_unanswered_hint_still_counts_then_the_solution_shows(
    make_study_runner: MakeStudy,
) -> None:
    run = await make_study_runner(_blocking(HINT_REQUEST))
    labels = []
    for _ in range(4):
        asked = await run.wait_question()
        labels.append(asked["options"][0]["label"])
        await run.resume("stuck")
    assert labels == ["Je bloque (1/3)", "Je bloque (2/3)", "Je bloque (3/3)", "Voir la solution"]
    await _end(run)
    assert run.store.finished is not None
    first = run.store.finished.outcomes[0]
    assert (first.verdict, first.hints) == ("revealed", 3)
    said = await _said(run)
    assert "Je n'ai pas pu préparer l'indice 1 sur 3." in " ".join(said)
    assert any(t.startswith("Je n'ai pas pu préparer l'indice 3 sur 3. Tu peux voir") for t in said)
    assert "Voici la solution :\n\nDes poids positifs qui somment à 1." in said
    assert run.models.blocked == 3


async def test_unanswered_section_is_shown_as_written(make_study_runner: MakeStudy) -> None:
    run = await make_study_runner(_blocking(TEACH_REQUEST))
    asked = await run.wait_question()
    assert asked["question"] == (
        "Que retiens-tu de la section « L'essentiel en 5 lignes » ? Dis-le avec tes mots."
    )
    section = next(t for t in await _said(run) if "telle qu'écrite dans la leçon" in t)
    assert SECTION_TEXTS[0] in section
    assert await run.events("board.update") == []
    await run.answer("Ma réponse détaillée.")
    await _end(run)
    assert run.store.finished is not None
    assert run.store.finished.outcomes[0].expected == SECTION_TEXTS[0]


async def test_unanswered_final_questions_come_from_the_lesson(
    make_study_runner: MakeStudy,
) -> None:
    run = await make_study_runner(_blocking(FINAL_REQUEST))
    await run.answer_all(QUESTIONS)
    await run.wait_question("finish_session")
    await run.resume("finish")
    await run.wait_status("completed")
    assert run.store.finished is not None
    finals = [o.question for o in run.store.finished.outcomes if o.phase == "final"]
    assert finals == [
        "Explique avec tes mots : Expliquer la softmax",
        "Explique avec tes mots : Lire une tête d'attention",
        "Que retiens-tu de la section « L'essentiel en 5 lignes » ? Dis-le avec tes mots.",
    ]
    assert FALLBACK_FINAL_INTRO in await _said(run)


async def test_unanswered_opening_question_is_left_without_reply(
    make_study_runner: MakeStudy, study_store: FakeStudyStore, user_id: str
) -> None:
    study_store.add(user_id, study_context(question="Pourquoi la softmax ?"))
    run = await make_study_runner(_blocking(REPLY_REQUEST))
    await run.wait_question()
    assert NO_REPLY in await _said(run)
    await _end(run, wait=False)


def test_final_questions_without_objectives_or_sections_are_still_three() -> None:
    context = study_context(sections=0, objectives=[])
    finals = final_questions_from_lesson(context, 3)
    assert [f["question"] for f in finals] == [
        f"Qu'as-tu retenu de « {MODULE} » ?",
        f"Quelle idée de « {MODULE} » vas-tu appliquer, et comment ?",
        f"Quelle erreur éviter avec « {MODULE} », et pourquoi ?",
    ]
    assert all(f["expected"].strip() for f in finals)  # le corrigé de l'exercice


def test_long_expected_answers_are_cut_on_a_word() -> None:
    cut = fallback.excerpt("mot " * 400)
    assert len(cut) <= fallback.MAX_EXPECTED_CHARS and cut.endswith("mot…")
