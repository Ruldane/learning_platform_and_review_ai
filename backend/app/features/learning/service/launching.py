"""Lancements des parcours d'un objectif et leurs relances après échec (D87, D97).

- `launch_program` : lance `program_builder` et passe l'objectif à « chosen » ; appelé sous le
  verrou de l'objectif par le port (`start_program`, nœud `finalize`) et par la route `choose`.
- `retry_program` : la route `choose` relance le Stratège quand le même choix est déjà fait, le
  Conseil fermé, et qu'il n'y a ni programme, ni session `program_builder` ouverte.
- `retry_council` : `POST /goals/{id}/council` relance depuis le début un Conseil en échec, en
  gardant l'objectif.

Journaux : identifiants seulement (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.council_port import Choice
from app.core.errors import AppError
from app.db.models.learning import Goal
from app.features.learning.repository import GoalRepository
from app.features.learning.schemas import GoalStarted
from app.features.learning.service import goals
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import find_active_session, find_latest_session, session_facts

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("running", "waiting_user", "paused")
MONDAY = 0


def program_input(goal_id: str, choice: Choice) -> dict[str, Any]:
    """Entrée de `program_builder` (`ProgramBuilderInput`) ; ids dédoublonnés dans l'ordre."""
    start = choice.start_date.isoformat() if choice.start_date is not None else None
    ids = list(dict.fromkeys(choice.proposal_ids))
    return {"goal_id": goal_id, "proposal_ids": ids, "start_date": start}


async def program_session(db: AsyncSession, user_id: str, goal_id: str) -> str | None:
    """Session du dernier programme écrit, sinon session `program_builder` ouverte, sinon
    `None` (rien en cours : un lancement est permis)."""
    await goals.owned_goal(db, user_id, goal_id)
    program = await GoalRepository(db, user_id).latest_program(goal_id)
    if program is not None and program[1] is not None:
        return program[1]
    return await find_active_session(
        db, user_id, graph=goals.PROGRAM_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )


async def launch_program(
    factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    user_id: str,
    goal_id: str,
    choice: Choice,
) -> str:
    """Lance `program_builder` puis passe l'objectif à « chosen ». L'appelant tient le verrou
    de l'objectif et a vérifié qu'aucun programme n'est en cours (`program_session`)."""
    session_id = await launcher.start(
        user_id,
        goals.PROGRAM_GRAPH,
        program_input(goal_id, choice),
        subject_type=goals.SUBJECT,
        subject_id=goal_id,
    )
    async with factory() as db:
        goal = await goals.owned_goal(db, user_id, goal_id)
        if goal.status == "council":
            goal.status = "chosen"
        await db.commit()
    return session_id


def _coming_monday(value: object) -> date | None:
    """Date de début reprise d'une entrée précédente, si c'est encore un lundi à venir."""
    try:
        start = date.fromisoformat(str(value))
    except ValueError:
        return None
    return start if start.weekday() == MONDAY and start >= date.today() else None


async def _previous_start(db: AsyncSession, user_id: str, goal_id: str) -> date | None:
    previous = await find_latest_session(
        db, user_id, graph=goals.PROGRAM_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )
    facts = None if previous is None else await session_facts(db, user_id, previous)
    return None if facts is None else _coming_monday(facts.input.get("start_date"))


async def retry_program(
    learning: LearningRuntime,
    user_id: str,
    goal_id: str,
    council_status: str,
    ids: Sequence[str],
    start: date | None,
) -> str | None:
    """Sous le verrou de l'objectif, le même choix étant déjà écrit : relance `program_builder`
    si le Conseil est fermé (`finalize` passé ou arrêté), qu'aucun Conseil n'est ouvert pour
    l'objectif, et qu'il n'y a ni programme ni session `program_builder` ouverte. Date de début :
    `start`, sinon celle de l'entrée précédente si c'est encore un lundi à venir. Rend la
    session lancée, `None` si rien n'est relancé."""
    if council_status in OPEN_STATUSES:
        return None
    async with learning.session_factory() as db:
        if await program_session(db, user_id, goal_id) is not None:
            return None
        if await goals.open_council(db, user_id, goal_id) is not None:
            return None
        start = start or await _previous_start(db, user_id, goal_id)
    action: Literal["choose", "mix"] = "mix" if len(ids) == 2 else "choose"
    choice = Choice(action, tuple(ids), start)
    session_id = await launch_program(
        learning.session_factory, learning.launcher, user_id, goal_id, choice
    )
    logger.info(
        "Programme relancé : utilisateur %s, objectif %s, session %s", user_id, goal_id, session_id
    )
    return session_id


def council_not_failed(status: str | None) -> AppError:
    return AppError(
        "council_not_failed",
        "Le Conseil de cet objectif n'a pas échoué : il n'y a rien à relancer.",
        409,
        {"status": status},
    )


def goal_already_chosen() -> AppError:
    return AppError(
        "goal_already_chosen",
        "Un programme a déjà été lancé pour cet objectif : le Conseil ne se relance plus.",
        409,
    )


async def _failed_council_goal(db: AsyncSession, user_id: str, goal_id: str) -> Goal:
    goal = await goals.owned_goal(db, user_id, goal_id)
    latest = await find_latest_session(
        db, user_id, graph=goals.COUNCIL_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )
    facts = None if latest is None else await session_facts(db, user_id, latest)
    status = None if facts is None else facts.status
    if status != "failed":
        raise council_not_failed(status)
    if goal.status != "council":
        raise goal_already_chosen()
    return goal


async def retry_council(learning: LearningRuntime, user_id: str, goal_id: str) -> GoalStarted:
    """Sous le verrou de l'objectif : la dernière session `learning_council` doit être `failed`
    (sinon 409 `council_not_failed`, avec son statut) et aucun programme lancé (409
    `goal_already_chosen`). Le Conseil repart du début : cadrage et compte rendu effacés, puis
    nouvelle session, rangée sur l'objectif. Les lots et tableaux du Conseil en échec restent en
    base ; ses propositions ne sont plus rendues ni choisissables (`latest_batch`)."""
    async with learning.goal_lock(user_id, goal_id):
        async with learning.session_factory() as db:
            goal = await _failed_council_goal(db, user_id, goal_id)
            goal.framing, goal.minutes = {}, None
            await db.commit()  # avant le lancement : le nœud `context` relit l'objectif
        session_id = await learning.launcher.start(
            user_id,
            goals.COUNCIL_GRAPH,
            {"goal_id": goal_id},
            subject_type=goals.SUBJECT,
            subject_id=goal_id,
        )
        async with learning.session_factory() as db:
            goal = await goals.owned_goal(db, user_id, goal_id)
            goal.council_session_id = session_id
            await db.commit()
            out = await goals.goal_out(db, user_id, goal)
    logger.info(
        "Conseil relancé : utilisateur %s, objectif %s, Conseil %s", user_id, goal_id, session_id
    )
    return GoalStarted(goal=out, session_id=session_id)
