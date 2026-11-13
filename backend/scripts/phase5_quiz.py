"""Étape « quiz » du contrôle de fin de phase 5 : le quiz du module est préparé, passé, noté, et ses
suites sont vérifiées (révisions, nouvel essai à J+2).

Les bonnes réponses ne sont exposées qu'après une tentative notée (`AttemptOut.results`), et un
nouvel essai n'est permis qu'à J+2 : le premier passage répond donc « au hasard » (premier choix,
réponses courtes) et le quiz est le plus souvent raté. Un passage suivant, dès que le nouvel essai
est ouvert, lit les bonnes réponses de la dernière tentative notée du même quiz (les questions
sont les mêmes, D101) et peut atteindre `valide`. Rien de ce qui est envoyé ou reçu n'apparaît
dans la sortie : seulement des étapes, des nombres et des identifiants."""

from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase5_rules import RETRY_DAYS, check_attempt, check_quiz
from scripts.phase5_steps import Etude, around

QUIZ_ANSWER = "Une réponse courte."


async def _quiz_ready(run: Run, st: Etude) -> dict[str, Any]:
    started = await expect_ok(run, "quiz", "POST", f"/modules/{st.module_id}/quiz")
    st.quiz_id = started["quiz_id"]
    quiz: dict[str, Any] = {}

    async def ready() -> bool:
        quiz.update(await expect_ok(run, "quiz", "GET", f"/quizzes/{st.quiz_id}"))
        if quiz["status"] == "failed":
            raise CheckFailed("quiz", f"Quiz {st.quiz_id} en échec.")
        return bool(quiz["status"] == "ready")

    await run.until("quiz", ready, "quiz jamais prêt")
    return quiz


async def known_answers(run: Run, st: Etude, quiz: dict[str, Any]) -> dict[str, str]:
    """`id de question -> bonne réponse` lues dans la dernière tentative notée du quiz ; vide
    quand il n'y en a pas encore (premier passage)."""
    graded = [a for a in quiz["attempts"] if a["status"] == "graded"]
    if not graded:
        return {}
    last = max(graded, key=lambda a: str(a["created_at"]))
    path = f"/quizzes/{st.quiz_id}/attempts/{last['id']}"
    previous = await expect_ok(run, "quiz", "GET", path)
    return {r["question_id"]: str(r["correct_answer"]) for r in previous["results"]}


def build_answers(quiz: dict[str, Any], known: dict[str, str]) -> list[dict[str, Any]]:
    """Une réponse par question, dans l'ordre affiché : la bonne quand elle est connue (le QCM par
    le rang de son texte dans les choix, mélangés à chaque essai), sinon le premier choix ou une
    réponse courte."""
    answers: list[dict[str, Any]] = []
    for question in quiz["questions"]:
        right = known.get(question["id"])
        if question["type"] == "qcm":
            index = question["choices"].index(right) if right in question["choices"] else 0
            answers.append({"question_id": question["id"], "choice": index})
        else:
            answers.append({"question_id": question["id"], "text": right or QUIZ_ANSWER})
    return answers


async def play_quiz(run: Run, st: Etude) -> None:
    quiz = await _quiz_ready(run, st)  # relu avant de répondre : l'ordre change à chaque essai
    check_quiz(quiz)
    known = await known_answers(run, st, quiz)
    path = f"/quizzes/{st.quiz_id}/attempts"

    async def send() -> dict[str, Any]:
        sent: dict[str, Any] = await expect_ok(
            run, "quiz", "POST", path, json={"answers": build_answers(quiz, known)}
        )
        return sent

    started, retry_days = await around(run, "quiz", send, RETRY_DAYS)
    st.attempt_id = started["attempt_id"]
    attempt: dict[str, Any] = {}

    async def graded() -> bool:
        attempt.update(await expect_ok(run, "quiz", "GET", f"{path}/{st.attempt_id}"))
        if attempt["status"] == "failed":
            raise CheckFailed("quiz", f"Tentative {st.attempt_id} en échec.")
        return bool(attempt["status"] == "graded")

    await run.until("quiz", graded, "tentative jamais notée")
    check_attempt(attempt, len(quiz["questions"]), retry_days)
    st.passed = bool(attempt["passed"])
    st.retry_on = str((attempt.get("followup") or {}).get("retry_on") or "")
    how = "bonnes réponses lues" if known else "premier passage"
    print(
        f"    note {attempt['score']} % ({how}) : {'réussi' if st.passed else 'raté'}", flush=True
    )
