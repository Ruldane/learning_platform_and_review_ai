"""Étapes du contrôle de fin de phase 5, partie « étude » (`check_phase5`) : le programme et la
leçon, la session guidée (réponses courtes, « Je bloque » quatre fois, « Passer », « Terminer »),
son bilan, le quiz du module et les fiches. Le contexte d'un passage est celui de la phase 4
(`Run`) ; les règles sont dans `phase5_rules`. Rien de ce qui est envoyé ou reçu n'apparaît dans
un message d'échec : seulement des étapes, des nombres, des codes et des identifiants."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase5_rules import (
    READING_TYPES,
    RETRY_DAYS,
    STUCK_LABELS,
    STUDY_DEAD,
    WORKED_MINUTES,
    check_attempt,
    check_quiz,
    check_study_summary,
    option_value,
)

QUESTION_KINDS = ("tutor_question", "finish_session")
DEAD_SESSION = ("failed", "cancelled", "completed")
MAX_TUTOR_QUESTIONS = 20
STUCK_AT, SKIP_AT = 2, 3  # rang de la question où January bloque quatre fois, puis où elle passe
SHORT_ANSWER = "Je dirais que ça normalise les scores en poids, en gros."
QUIZ_ANSWER = "Une réponse courte."


@dataclass
class Etude:
    """Ce que les étapes se passent : la leçon choisie, la session d'étude, le quiz."""

    lessons: dict[str, str] = field(default_factory=dict)  # leçons prêtes : id -> id du module
    lesson_id: str = ""
    reading: set[str] = field(default_factory=set)  # tâches de lecture du bloc, à voir cochées
    study_id: str = ""
    session_id: str = ""
    quiz_id: str = ""
    due_before: set[str] = field(default_factory=set)  # fiches dues avant la session

    @property
    def module_id(self) -> str:
        return self.lessons[self.lesson_id]


async def pick_program(run: Run, st: Etude) -> None:
    """Un programme validé avec une leçon prête ; le bloc du jour décide de la leçon quand il en
    a une (ses tâches de lecture doivent être cochées à la fin)."""
    programs = await expect_ok(run, "programme", "GET", "/programs")
    for program in (p for p in programs if p["status"] == "validated"):
        found = await expect_ok(run, "programme", "GET", f"/programs/{program['id']}/lessons")
        ready = {
            lesson["id"]: lesson["module_id"] for lesson in found if lesson["status"] == "ready"
        }
        if ready:
            run.program_id, st.lessons = program["id"], ready
            break
    else:
        raise CheckFailed(
            "programme", "Aucun programme validé avec une leçon prête. Lance d'abord "
            "scripts.check_phase4 ou --with-phase4."
        )  # fmt: skip
    summary = await expect_ok(run, "programme", "GET", "/study-sessions/summary")
    if summary.get("open_session_id"):
        raise CheckFailed(
            "programme", f"Session d'étude déjà ouverte ({summary['open_session_id']}) : "
            "termine-la ou abandonne-la d'abord."
        )  # fmt: skip
    st.lesson_id = next(iter(st.lessons))
    block = summary.get("block")
    if block and block["lesson_id"] in st.lessons:
        st.lesson_id = block["lesson_id"]
        st.reading = {t["title"] for t in block["tasks"] if t["type"] in READING_TYPES}


async def next_question(run: Run, step: str, session_id: str, seen: set[str]) -> dict[str, Any]:
    """La question suivante du Tuteur (ou la fin de séance), pas encore vue ; échec si la session
    d'agents s'arrête avant."""
    found: dict[str, Any] = {}

    async def asked() -> bool:
        view = await expect_ok(run, step, "GET", f"/sessions/{session_id}")
        if view["status"] in DEAD_SESSION:
            code = (view.get("error") or {}).get("code", "aucun")
            raise CheckFailed(step, f"Session {session_id} arrêtée ({view['status']}, {code}).")
        question = view.get("pending_interrupt") or {}
        fresh = question.get("interrupt_id") not in seen
        if view["status"] == "waiting_user" and question.get("kind") in QUESTION_KINDS and fresh:
            found.update(question)
            return True
        return False

    await run.until(step, asked, "question du Tuteur jamais posée")
    seen.add(found["interrupt_id"])
    return found


async def _resume(run: Run, st: Etude, question: dict[str, Any], value: Any) -> None:
    body = {"interrupt_id": question["interrupt_id"], "value": value}
    await expect_ok(run, "session", "POST", f"/sessions/{st.session_id}/resume", json=body)


async def _stuck(run: Run, st: Etude, seen: set[str], question: dict[str, Any]) -> dict[str, Any]:
    """Quatre « Je bloque » : trois indices (libellés 1/3 à 3/3), puis la solution ; la question
    suivante repart du compte à zéro."""
    for label in STUCK_LABELS:
        value = option_value(question, "stuck", label)
        await _resume(run, st, question, value)
        question = await next_question(run, "session", st.session_id, seen)
    if question["kind"] == "tutor_question":
        option_value(question, "stuck", STUCK_LABELS[0])
    return question


async def _play(run: Run, st: Etude) -> int:
    """Répond aux questions du Tuteur jusqu'à la fin de séance ; rend leur nombre."""
    seen: set[str] = set()
    question = await next_question(run, "session", st.session_id, seen)
    asked = 0
    while question["kind"] == "tutor_question":
        asked += 1
        if asked > MAX_TUTOR_QUESTIONS:
            raise CheckFailed(
                "session", f"Plus de {MAX_TUTOR_QUESTIONS} questions : séance sans fin."
            )
        if asked == STUCK_AT:
            question = await _stuck(run, st, seen, question)
            continue
        if asked == SKIP_AT:
            value: Any = option_value(question, "skip")
        else:
            value = {"answers": {"answer": SHORT_ANSWER}}
        await _resume(run, st, question, value)
        question = await next_question(run, "session", st.session_id, seen)
    return asked


async def _wait_finished(run: Run, st: Etude) -> None:
    async def finished() -> bool:
        view = await expect_ok(run, "session", "GET", f"/study-sessions/{st.study_id}")
        if view["status"] in STUDY_DEAD:
            agents = await expect_ok(run, "session", "GET", f"/sessions/{st.session_id}")
            code = (agents.get("error") or {}).get("code", "aucun")
            raise CheckFailed(
                "session", f"Session d'étude {st.study_id} {view['status']} "
                f"(session d'agents {agents['status']}, {code})."
            )  # fmt: skip
        return bool(view["status"] == "finished")

    await run.until("session", finished, "session d'étude jamais finie")


async def play_session(run: Run, st: Etude) -> None:
    due = await expect_ok(run, "session", "GET", "/flashcards/due")
    st.due_before = {card["id"] for card in due["cards"]}
    body = {"lesson_id": st.lesson_id, "mode": "socratic"}
    started = await expect_ok(run, "session", "POST", "/study-sessions", json=body)
    st.study_id, st.session_id = started["study_session_id"], started["session_id"]
    asked = await _play(run, st)
    if asked < SKIP_AT:
        raise CheckFailed("session", f"{asked} question(s) seulement : {SKIP_AT} au moins.")
    finish = {"action": "finish", "worked_minutes": WORKED_MINUTES}
    await expect_ok(run, "session", "PATCH", f"/study-sessions/{st.study_id}", json=finish)
    await _wait_finished(run, st)


async def check_balance(run: Run, st: Etude) -> None:
    study = await expect_ok(run, "bilan de session", "GET", f"/study-sessions/{st.study_id}")
    program = await expect_ok(run, "bilan de session", "GET", f"/programs/{run.program_id}")
    check_study_summary(study, program, st.reading)


async def _local_today(run: Run, step: str) -> date:
    settings = await expect_ok(run, step, "GET", "/settings")
    return datetime.now(ZoneInfo(settings["timezone"])).date()


async def around[T](
    run: Run, step: str, action: Callable[[], Awaitable[T]], days: int
) -> tuple[T, set[date]]:
    """Le résultat de `action` et les jours « aujourd'hui + `days` » acceptés (heure locale de
    January, lue avant et après : un minuit peut tomber pendant l'appel)."""
    before = await _local_today(run, step)
    result = await action()
    after = await _local_today(run, step)
    return result, {before + timedelta(days=days), after + timedelta(days=days)}


async def _quiz_ready(run: Run, st: Etude) -> dict[str, Any]:
    path = f"/modules/{st.module_id}/quiz"
    started = await expect_ok(run, "quiz", "POST", path)
    st.quiz_id = started["quiz_id"]
    quiz: dict[str, Any] = {}

    async def ready() -> bool:
        quiz.update(await expect_ok(run, "quiz", "GET", f"/quizzes/{st.quiz_id}"))
        if quiz["status"] == "failed":
            raise CheckFailed("quiz", f"Quiz {st.quiz_id} en échec.")
        return bool(quiz["status"] == "ready")

    await run.until("quiz", ready, "quiz jamais prêt")
    return quiz


def _answers(quiz: dict[str, Any]) -> list[dict[str, Any]]:
    """Une réponse courte à chaque question, dans l'ordre affiché ; le premier choix aux QCM."""
    return [
        {"question_id": q["id"], "choice": 0}
        if q["type"] == "qcm"
        else {"question_id": q["id"], "text": QUIZ_ANSWER}
        for q in quiz["questions"]
    ]


async def play_quiz(run: Run, st: Etude) -> None:
    quiz = await _quiz_ready(run, st)  # relu avant de répondre : l'ordre change à chaque essai
    check_quiz(quiz)
    path = f"/quizzes/{st.quiz_id}/attempts"

    async def send() -> dict[str, Any]:
        sent: dict[str, Any] = await expect_ok(
            run, "quiz", "POST", path, json={"answers": _answers(quiz)}
        )
        return sent

    started, retry_days = await around(run, "quiz", send, RETRY_DAYS)
    attempt: dict[str, Any] = {}

    async def graded() -> bool:
        attempt.update(await expect_ok(run, "quiz", "GET", f"{path}/{started['attempt_id']}"))
        if attempt["status"] == "failed":
            raise CheckFailed("quiz", f"Tentative {started['attempt_id']} en échec.")
        return bool(attempt["status"] == "graded")

    await run.until("quiz", graded, "tentative jamais notée")
    check_attempt(attempt, len(quiz["questions"]), retry_days)


async def check_cards(run: Run, st: Etude) -> None:
    """Un avis « fail » sur une fiche due : elle revient le lendemain local. Sans fiche due,
    aucune fiche créée par ce passage (session, quiz) n'est due aujourd'hui : elles sont à J+1."""
    due = await expect_ok(run, "fiches", "GET", "/flashcards/due")
    if not due["cards"]:
        return
    fresh = {card["id"] for card in due["cards"]} - st.due_before
    if fresh:
        raise CheckFailed("fiches", f"{len(fresh)} fiche(s) créée(s) par ce passage déjà dues.")
    card_id = due["cards"][0]["id"]

    async def review() -> dict[str, Any]:
        body = {"result": "fail"}
        out: dict[str, Any] = await expect_ok(
            run, "fiches", "POST", f"/flashcards/{card_id}/review", json=body
        )
        return out

    reviewed, tomorrow = await around(run, "fiches", review, 1)
    if reviewed["due_date"] not in {day.isoformat() for day in tomorrow}:
        raise CheckFailed("fiches", f"Fiche {card_id} due le {reviewed['due_date']} : demain.")
