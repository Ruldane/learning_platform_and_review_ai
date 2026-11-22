"""Deux corrections fictives, issues de tentatives et d’évaluations déjà terminées."""

from datetime import date, datetime

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow
from app.db.models.daily import Project
from app.db.models.learning import Goal
from app.db.models.program import Module, Program, Week
from app.db.models.study import Quiz, QuizAttempt, QuizQuestion

QUIZ_TITLE = "Quiz sur les données manquantes"
PROJECT_TITLE = "Contrôle d’un jeu de données"
QUIZ_FINDING = "La correction distingue la valeur zéro de l’absence de valeur."
PROJECT_FINDING = "Le contrôle confond les lignes sans valeur avec les valeurs nulles."
HYPOTHESIS = "Valeurs manquantes"


async def _module(db: AsyncSession, user_id: str) -> Module:
    today = date.today()
    goal = Goal(
        user_id=user_id, text="Contrôler les données", target_role="Analyste", status="planned"
    )
    db.add(goal)
    await db.flush()
    program = Program(
        user_id=user_id,
        goal_id=goal.id,
        status="validated",
        title="Données",
        start_date=today,
        weekly_minutes=120,
        cap_minutes=100,
    )
    db.add(program)
    await db.flush()
    week = Week(
        user_id=user_id,
        program_id=program.id,
        rank=1,
        theme="Contrôle",
        objective="Distinguer",
        deliverable="Jeu de données",
        start_date=today,
    )
    db.add(week)
    await db.flush()
    module = Module(
        user_id=user_id,
        program_id=program.id,
        week_id=week.id,
        rank=0,
        title="Valeurs absentes",
        skills=["Nettoyage des données"],
    )
    db.add(module)
    await db.flush()
    return module


def _questions(db: AsyncSession, quiz: Quiz) -> tuple[str, str]:
    failed, passed = new_id(), new_id()
    for rank, item_id, prompt in (
        (1, failed, "Comment distinguer zéro d’une valeur manquante ?"),
        (2, passed, "Comment trouver le nombre de lignes renseignées ?"),
    ):
        db.add(
            QuizQuestion(
                id=item_id,
                user_id=quiz.user_id,
                quiz_id=quiz.id,
                rank=rank,
                type="short",
                prompt=prompt,
                skill="Contrôle des données",
                expected=("Traiter les cas séparément." if rank == 1 else "Dénombrer."),
                rubric=["Décrire la méthode et justifier le résultat."],
            )
        )
    return failed, passed


def _assessed_project(module: Module, now: datetime) -> Project:
    return Project(
        user_id=module.user_id,
        module_id=module.id,
        program_id=module.program_id,
        title=PROJECT_TITLE,
        status="to_redo",
        brief={
            "title": PROJECT_TITLE,
            "context": "Jeu de données de recette.",
            "objective": "Distinguer les valeurs absentes.",
            "constraints": ["Contrôler le jeu local.", "Conserver les lignes."],
            "criteria": [
                "Reconnaître une valeur manquante.",
                "Dénombrer.",
                "Décrire le résultat.",
            ],
            "hours": 3,
            "deliverable": "description",
        },
        submissions=[{"at": now.isoformat(), "description": "Compte rendu de recette."}],
        evaluation={
            "session_id": new_id(),
            "at": now.isoformat(),
            "verdict": "to_redo",
            "results": [{"index": 1, "met": False, "comment": PROJECT_FINDING}],
        },
    )


async def seed_evidence(app: FastAPI, user_id: str | None = None) -> tuple[str, str]:
    owner = user_id or app.state.local_user_id
    now = utcnow()
    async with app.state.session_factory() as db:
        module = await _module(db, owner)
        quiz = Quiz(
            user_id=owner,
            module_id=module.id,
            program_id=module.program_id,
            title=QUIZ_TITLE,
            status="ready",
        )
        db.add(quiz)
        await db.flush()
        failed_question, passed_question = _questions(db, quiz)
        attempt = QuizAttempt(
            user_id=owner,
            quiz_id=quiz.id,
            status="graded",
            score=50,
            graded_at=now,
            results=[
                {
                    "question_id": failed_question,
                    "points": 0,
                    "correct_answer": "Traiter les cas séparément.",
                    "explanation": "Une absence de valeur n'indique aucune valeur mesurée.",
                    "feedback": QUIZ_FINDING,
                },
                {
                    "question_id": passed_question,
                    "points": 1,
                    "correct_answer": "Dénombrer.",
                    "explanation": "",
                    "feedback": "Correct.",
                },
            ],
        )
        project = _assessed_project(module, now)
        db.add_all([attempt, project])
        await db.commit()
        return quiz.id, passed_question
