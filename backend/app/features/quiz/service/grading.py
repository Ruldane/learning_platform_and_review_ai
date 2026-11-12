"""Note d'une tentative (SPEC F9, D101), rangée par le port de l'Examinateur en UNE transaction,
sous le verrou du programme pris AVANT elle (F4), gardée par `UPDATE … SET status='graded' WHERE
status='grading'` : rejouée, elle relit la note et n'écrit rien de plus.

≥ 80 % : compétences du module à `valide` (preuve `quiz`, `ref_id` = le quiz, F21), échecs de
fiches remis à 0, reflet dans la mémoire après le commit. < 80 % : révisions ciblées (« Réviser :
{compétence} », dès demain) et nouvel essai (« Refaire le quiz : {module} », à J+2) posés dans le
budget, `retry_on` = J+2 local. Toujours : fiches depuis les erreurs, tâches « Refaire le quiz »
du module cochées (F18), tâche `quiz` de la semaine cochée quand tous ses modules sont notés,
ligne de journal `quiz`. Journaux : identifiants et nombres seulement."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.quiz_port import GradedSaved
from app.core.skills import evidence
from app.db.models.program import Module
from app.db.models.study import Quiz, QuizAttempt, QuizQuestion
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.program.service.followup import (
    FollowupTask,
    add_followup,
    retry_title,
    tick_retry,
    tick_week_quiz,
)
from app.features.program.service.runtime import ProgramRuntime
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.quiz.service.scoring import OPEN_SCORES, passed, qcm_points, score_percent
from app.features.quiz.service.scoring import weak_skills as weakest
from app.features.skills.service import SkillsService

RETRY_DAYS = 2
REVISION_MINUTES = 20
MISSING_FEEDBACK = "Réponse non évaluée : relis la correction."


@dataclass(frozen=True)
class GradeContext:
    """Ce que la note lit, sous le verrou : la tentative, son quiz, son module, ses questions."""

    attempt: QuizAttempt
    quiz: Quiz
    module: Module
    questions: list[QuizQuestion]


def module_skills(ctx: GradeContext) -> list[str]:
    """Compétences du module ; à défaut, celles des questions."""
    skills = [str(s) for s in ctx.module.skills] or [q.skill for q in ctx.questions]
    return list(dict.fromkeys(skills))


def _correct(question: QuizQuestion) -> str:
    if question.type == "qcm" and question.correct_index is not None:
        choices = [str(c) for c in question.choices]
        if 0 <= question.correct_index < len(choices):
            return choices[question.correct_index]
    return question.expected


def results_of(ctx: GradeContext, grades: Mapping[str, tuple[float, str]]) -> list[dict[str, Any]]:
    """Une correction par question, dans l'ordre d'origine. QCM : point recalculé par le code ;
    ouverte : la note de l'Examinateur, ramenée à 0 hors de {0 ; 0,5 ; 1}."""
    answers = {a["question_id"]: a for a in ctx.attempt.answers if isinstance(a, dict)}
    out: list[dict[str, Any]] = []
    for q in ctx.questions:
        answer = answers.get(q.id, {})
        if q.type == "qcm":
            points, feedback = qcm_points(q.correct_index, answer.get("choice")), ""
        else:
            points, feedback = grades.get(f"q{q.rank}", (0.0, MISSING_FEEDBACK))
            points = float(points) if float(points) in OPEN_SCORES else 0.0
        out.append(
            {
                "question_id": q.id,
                "points": points,
                "correct_answer": _correct(q),
                "explanation": q.explanation,
                "feedback": feedback,
            }
        )
    return out


def error_cards(ctx: GradeContext, results: Sequence[Mapping[str, Any]]) -> list[NewCard]:
    """Une fiche par question manquée : recto = énoncé (et code), verso = réponse attendue et
    explication."""
    cards: list[NewCard] = []
    for q, result in zip(ctx.questions, results, strict=True):
        if result["points"] >= 1:
            continue
        front = q.prompt if not q.code else f"{q.prompt}\n\n{q.code}"
        cards.append(
            NewCard(
                front=front,
                back=f"{result['correct_answer']}\n\n{q.explanation}".strip(),
                skill=q.skill,
                module_id=ctx.module.id,
                source="quiz",
                source_id=ctx.attempt.id,
            )
        )
    return cards


def followup_tasks(ctx: GradeContext, points: Sequence[float], today: date) -> list[FollowupTask]:
    """Révisions des compétences faibles (3 au plus) dès demain, puis le nouvel essai à J+2."""
    weak = weakest([q.skill for q in ctx.questions], points)
    tasks = [
        FollowupTask(
            f"Réviser : {skill}",
            "lire",
            REVISION_MINUTES,
            "Leçon relue sur ce point et fiches revues.",
            today + timedelta(days=1),
        )
        for skill in weak
    ]
    tasks.append(
        FollowupTask(
            retry_title(ctx.module.title),
            "quiz",
            REVISION_MINUTES,
            "Quiz refait, 80 % ou plus.",
            today + timedelta(days=RETRY_DAYS),
        )
    )
    return tasks


def journal_text(module: str, score: int, ok: bool, revisions: int, retry: date | None) -> str:
    if ok:
        return f"Quiz « {module} » : {score} % — acquis validés."
    done = f"{revisions} révision{'s' if revisions > 1 else ''} et " if revisions else ""
    when = f"un nouvel essai le {retry:%d/%m}." if retry else "un nouvel essai dans 2 jours."
    return f"Quiz « {module} » : {score} % — {done}{when}"


async def _followup(
    db: AsyncSession, program: ProgramRuntime, ctx: GradeContext, points: list[float], today: date
) -> tuple[dict[str, Any], int]:
    """Révisions puis nouvel essai posés dans le budget ; rend le suivi et le nombre de tâches
    posées. Les révisions ont mêmes durée, type et premier jour : si l'une ne tient pas, les
    suivantes non plus, donc les posées sont les premières."""
    *revisions, retry = followup_tasks(ctx, points, today)
    user_id, module_id = ctx.attempt.user_id, ctx.module.id
    days, unplaced = await add_followup(db, program, user_id, module_id, revisions)
    retry_days, retry_unplaced = await add_followup(db, program, user_id, module_id, [retry])
    followup = {
        "revision_tasks": [t.title for t in revisions[: len(days)]],
        "retry_on": (today + timedelta(days=RETRY_DAYS)).isoformat(),
        "unplaced": unplaced + retry_unplaced,
    }
    return followup, len(days) + len(retry_days)


async def grade(
    db: AsyncSession,
    program: ProgramRuntime,
    ctx: GradeContext,
    grades: Mapping[str, tuple[float, str]],
    now: datetime,
    today: date,
) -> GradedSaved:
    """Range la note (la tentative vient d'être réclamée `graded`) ; ne commite pas."""
    attempt, user_id = ctx.attempt, ctx.attempt.user_id
    results = results_of(ctx, grades)
    points = [float(r["points"]) for r in results]
    score = score_percent(points)
    ok = passed(score)
    cards = await add_cards(db, user_id, error_cards(ctx, results), today)
    await tick_retry(db, program, user_id, ctx.module.id)
    followup: dict[str, Any] = {"revision_tasks": [], "retry_on": None, "unplaced": 0}
    placed = 0
    if ok:
        skills = SkillsService(db, user_id)
        label = f"Quiz « {ctx.module.title} » : {score} % ({today:%d/%m})"
        await skills.raise_levels(
            module_skills(ctx), "valide", evidence("quiz", ctx.quiz.id, label, now)
        )
        await skills.reset_fail_streaks(module_skills(ctx))
    else:
        followup, placed = await _followup(db, program, ctx, points, today)
    attempt.score, attempt.results, attempt.graded_at = score, results, now
    # Comptes gardés pour un rejeu (l'annonce relit la même chose) ; hors du contrat.
    attempt.followup = followup | {"tasks_added": placed, "cards_created": cards}
    attempt.retry_on = None if ok else today + timedelta(days=RETRY_DAYS)
    await db.flush()
    await tick_week_quiz(db, program, user_id, ctx.module.id)
    revisions = len(followup["revision_tasks"])
    await add_entry(
        db,
        user_id,
        kind="quiz",
        text=journal_text(ctx.module.title, score, ok, revisions, attempt.retry_on),
        occurred_on=today,
        ref_key=f"quiz:{attempt.id}",
        links=JournalLinks(session_id=attempt.session_id, quiz_attempt_id=attempt.id),
        data={"quiz_id": ctx.quiz.id, "score": score, "passed": ok},
    )
    return GradedSaved(attempt.id, score, ok, cards, placed)


def saved_of(attempt: QuizAttempt) -> GradedSaved:
    """La note déjà rangée (rejeu) : rien n'est réécrit."""
    score = attempt.score or 0
    followup = attempt.followup or {}
    cards, placed = int(followup.get("cards_created", 0)), int(followup.get("tasks_added", 0))
    return GradedSaved(attempt.id, score, passed(score), cards, placed)
