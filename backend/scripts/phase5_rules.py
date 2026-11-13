"""Règles du contrôle de fin de phase 5, partie « étude » (`check_phase5`), en fonctions pures :
chacune lit des réponses de l'API déjà reçues et lève `CheckFailed` quand une règle n'est pas
tenue. Les messages ne portent que des étapes, des nombres et des identifiants : jamais une
question, une réponse, une fiche ni un titre."""

from collections.abc import Iterable
from datetime import date
from typing import Any

from scripts.phase4_rules import CheckFailed

WORKED_MINUTES = 30  # minutes envoyées à « Terminer »
MIN_QUESTIONS, MAX_QUESTIONS = 8, 12
MIN_TYPES = 3
PASS_SCORE = 80
RETRY_DAYS = 2
READING_TYPES = ("lire", "regarder")
# Libellés de l'option « Je bloque » : le back compte les indices (F15).
STUCK_LABELS = ("Je bloque (1/3)", "Je bloque (2/3)", "Je bloque (3/3)", "Voir la solution")
STUDY_DEAD = ("interrupted", "cancelled")


def option_value(question: dict[str, Any], value: str, label: str | None = None) -> str:
    """La valeur de l'option `value` de la question (la réponse se donne par la valeur, jamais
    par le libellé) ; `label` : le libellé que le back doit lui avoir donné."""
    found = [o for o in question.get("options") or [] if o.get("value") == value]
    if not found:
        raise CheckFailed("session", f"Option « {value} » absente de la question.")
    if label is not None and found[0].get("label") != label:
        raise CheckFailed("session", f"Option « {value} » au mauvais libellé (attendu {label!r}).")
    return str(found[0]["value"])


def check_quiz(quiz: dict[str, Any]) -> None:
    """8 à 12 questions, au moins 3 types, un QCM a 3 à 5 choix, les autres types aucun."""
    questions = quiz["questions"]
    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        raise CheckFailed("quiz", f"{len(questions)} question(s) : 8 à 12 attendues.")
    types = {q["type"] for q in questions}
    if len(types) < MIN_TYPES:
        raise CheckFailed("quiz", f"{len(types)} type(s) de questions : 3 au moins.")
    for question in questions:
        choices = len(question["choices"])
        if question["type"] == "qcm" and not 3 <= choices <= 5:
            raise CheckFailed(
                "quiz", f"QCM n° {question['rank']} : {choices} choix, 3 à 5 attendus."
            )
        if question["type"] != "qcm" and choices:
            raise CheckFailed("quiz", f"Question n° {question['rank']} : des choix hors QCM.")
        if question["type"] == "code" and not (question.get("code") or "").strip():
            raise CheckFailed(
                "quiz", f"Question n° {question['rank']} : lecture de code sans code."
            )


def _check_results(attempt: dict[str, Any], count: int) -> None:
    results = attempt["results"]
    if len(results) != count:
        raise CheckFailed("quiz", f"{len(results)} résultat(s) pour {count} question(s).")
    for number, result in enumerate(results, start=1):
        points = result["points"]
        if not 0 <= points <= 1:
            raise CheckFailed("quiz", f"Résultat n° {number} : {points} point(s), 0 à 1 attendu.")
        if points < 1 and not str(result.get("explanation") or "").strip():
            raise CheckFailed("quiz", f"Résultat n° {number} sous 1 point sans explication.")


def check_attempt(attempt: dict[str, Any], count: int, retry_days: Iterable[date]) -> None:
    """Tentative notée : note entière de 0 à 100, une correction par question (une explication
    sous 1 point) ; ≥ 80 % : aucune révision ; sinon révisions et nouvel essai à J+2 local
    (`retry_days` : les jours acceptés, autour d'un minuit)."""
    score = attempt["score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise CheckFailed("quiz", "Note absente ou hors de 0 à 100.")
    ok = score >= PASS_SCORE
    if attempt["passed"] is not ok:
        raise CheckFailed("quiz", f"Note de {score} % : « réussi » incohérent.")
    _check_results(attempt, count)
    followup = attempt.get("followup")
    if ok:
        if followup and (followup["revision_tasks"] or followup["retry_on"]):
            raise CheckFailed("quiz", f"Note de {score} % : des révisions pour un quiz réussi.")
        return
    if not followup or not (followup["revision_tasks"] or followup["unplaced"]):
        raise CheckFailed("quiz", f"Note de {score} % : aucune révision posée.")
    wanted = {day.isoformat() for day in retry_days}
    if followup["retry_on"] not in wanted:
        raise CheckFailed("quiz", f"Nouvel essai le {followup['retry_on']} : J+2 attendu.")


def program_tasks(program: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        task for week in program["weeks"] for module in week["modules"] for task in module["tasks"]
    ]


def check_study_summary(study: dict[str, Any], program: dict[str, Any], reading: set[str]) -> None:
    """Session finie : 1 à 30 minutes, une fiche au moins, des tâches cochées qui sont `done`
    dans le programme (et celles de lecture du bloc, quand il y en avait)."""
    if study["status"] in STUDY_DEAD:
        raise CheckFailed("bilan de session", f"Session d'étude {study['status']}.")
    if study["status"] != "finished":
        raise CheckFailed("bilan de session", f"Session d'étude {study['status']}, pas finie.")
    if not 1 <= study["minutes"] <= WORKED_MINUTES:
        raise CheckFailed("bilan de session", f"{study['minutes']} minute(s) : 1 à 30 attendues.")
    if study["flashcards_created"] < 1:
        raise CheckFailed("bilan de session", "Aucune fiche créée.")
    done = {task["title"] for task in program_tasks(program) if task["status"] == "done"}
    ticked = set(study["tasks_done"])
    if reading and not ticked:
        raise CheckFailed("bilan de session", "Aucune tâche cochée.")
    if missing := len(ticked - done):
        raise CheckFailed("bilan de session", f"{missing} tâche(s) cochée(s) pas `done`.")
    if absent := len(reading - ticked):
        raise CheckFailed(
            "bilan de session", f"{absent} tâche(s) de lecture du bloc non cochée(s)."
        )
