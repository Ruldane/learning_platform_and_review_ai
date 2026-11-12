"""Objectifs (SPEC 3.1, étape 1) : création, qui lance le Conseil (`learning_council`), et
lectures. Écritures du port pour l'objectif (cadrage, compte rendu).

Journaux : identifiants seulement, jamais le texte d'un objectif ni une réponse (SPEC 17.2)."""

import builtins
import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.council_port import FramingQuestion, GoalBrief
from app.core.errors import AppError
from app.db.models.learning import Goal
from app.features.learning.repository import GoalRepository
from app.features.learning.schemas import GoalCreate, GoalOut, GoalStarted
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import find_active_session, find_latest_session

logger = logging.getLogger(__name__)

COUNCIL_GRAPH = "learning_council"
PROGRAM_GRAPH = "program_builder"
SUBJECT = "goal"


def goal_not_found() -> AppError:
    return AppError("goal_not_found", "Objectif introuvable.", 404)


async def owned_goal(db: AsyncSession, user_id: str, goal_id: str) -> Goal:
    """L'objectif de l'utilisateur, relu (frais) ; 404 s'il n'existe pas ou est à un autre."""
    goal = await GoalRepository(db, user_id).get_fresh(goal_id)
    if goal is None:
        raise goal_not_found()
    return goal


async def program_of(db: AsyncSession, user_id: str, goal_id: str) -> tuple[str | None, str | None]:
    """`(programme, session program_builder)` de l'objectif : le dernier programme écrit et sa
    session, sinon la dernière session `program_builder` lancée (le Stratège n'a encore rien
    enregistré, ou elle a échoué)."""
    program = await GoalRepository(db, user_id).latest_program(goal_id)
    if program is not None and program[1] is not None:
        return program
    session = await find_latest_session(
        db, user_id, graph=PROGRAM_GRAPH, subject_type=SUBJECT, subject_id=goal_id
    )
    return (program[0] if program else None, session)


async def goal_out(db: AsyncSession, user_id: str, goal: Goal) -> GoalOut:
    program_id, program_session_id = await program_of(db, user_id, goal.id)
    weekly = goal.weekly_minutes
    return GoalOut(
        id=goal.id,
        text=goal.text,
        target_role=goal.target_role,
        deadline=goal.deadline,
        weekly_hours=None if weekly is None else weekly // 60,
        status=goal.status,  # type: ignore[arg-type]  # colonne texte, valeurs de GoalStatus
        council_session_id=goal.council_session_id,
        program_id=program_id,
        program_session_id=program_session_id,
        created_at=goal.created_at,
    )


async def create_goal(
    db: AsyncSession, learning: LearningRuntime, user_id: str, req: GoalCreate
) -> GoalStarted:
    """Enregistre l'objectif puis lance son Conseil (aucune route de session à part, D87).
    L'objectif est commité AVANT le lancement : le nœud `context` le relit dans sa propre
    session. Lancement impossible (moteur indisponible) : l'objectif est retiré, l'erreur
    passe."""
    repo = GoalRepository(db, user_id)
    weekly = None if req.weekly_hours is None else req.weekly_hours * 60
    goal = await repo.add(
        text=req.text,
        target_role=req.target_role,
        deadline=req.deadline,
        weekly_minutes=weekly,
        status="council",
        framing={},
    )
    await db.commit()
    try:
        session_id = await learning.launcher.start(
            user_id, COUNCIL_GRAPH, {"goal_id": goal.id}, subject_type=SUBJECT, subject_id=goal.id
        )
    except AppError:
        await repo.delete(goal.id)
        await db.commit()
        raise
    goal.council_session_id = session_id
    await db.commit()  # verrou d'écriture de SQLite rendu aussitôt : le Conseil écrit déjà
    logger.info(
        "Objectif créé : utilisateur %s, objectif %s, Conseil %s", user_id, goal.id, session_id
    )
    return GoalStarted(goal=await goal_out(db, user_id, goal), session_id=session_id)


async def list_goals(db: AsyncSession, user_id: str) -> builtins.list[GoalOut]:
    goals = await GoalRepository(db, user_id).list_recent()
    return [await goal_out(db, user_id, goal) for goal in goals]


async def get_goal(db: AsyncSession, user_id: str, goal_id: str) -> GoalOut:
    return await goal_out(db, user_id, await owned_goal(db, user_id, goal_id))


async def open_council(db: AsyncSession, user_id: str, goal_id: str) -> str | None:
    """Session du Conseil de l'objectif encore ouverte, `None` sinon."""
    return await find_active_session(
        db, user_id, graph=COUNCIL_GRAPH, subject_type=SUBJECT, subject_id=goal_id
    )


# --- Écritures du port (`AgentCouncilStore`) --------------------------------------------


def brief_of(goal: Goal) -> GoalBrief:
    answers = goal.framing.get("answers") if isinstance(goal.framing, dict) else None
    return GoalBrief(
        goal_id=goal.id,
        text=goal.text,
        target_role=goal.target_role,
        deadline=goal.deadline,
        weekly_minutes=goal.weekly_minutes,
        framing=dict(answers) if isinstance(answers, dict) else {},
    )


async def save_framing(
    db: AsyncSession,
    user_id: str,
    goal_id: str,
    questions: Sequence[FramingQuestion],
    answers: Mapping[str, str],
) -> None:
    """Questions et réponses du cadrage ; écrase les précédentes (idempotent)."""
    goal = await owned_goal(db, user_id, goal_id)
    goal.framing = {
        "questions": [{"id": q.id, "question": q.question} for q in questions],
        "answers": dict(answers),
    }
    await db.flush()


async def save_minutes(db: AsyncSession, user_id: str, goal_id: str, text: str) -> None:
    goal = await owned_goal(db, user_id, goal_id)
    goal.minutes = text
    await db.flush()
