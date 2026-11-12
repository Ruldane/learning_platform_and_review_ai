"""Choix du parcours (SPEC 3.1, étape 6 ; point d'arrêt n° 2, D85, D87).

La route écrit le choix puis reprend l'interruption `choose_path` ; le nœud `finalize` du
Conseil réécrit le même choix (`write_choice`, la même écriture) et lance seul `program_builder`
par le port. La reprise générique (`/sessions/{id}/resume`) reste possible : tout passe par
`finalize`, sous le verrou de l'objectif (`LearningRuntime.goal_lock`), donc un seul programme.

Lectures et écritures en sessions courtes ouvertes sous le verrou : la requête qui attendait le
verrou voit ce que la précédente a commité (double clic : même état rendu, rien de relancé)."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.council_port import Choice
from app.core.errors import AppError
from app.features.learning.repository import ProposalRepository
from app.features.learning.schemas import ChooseOut, ChooseRequest
from app.features.learning.service.goals import owned_goal
from app.features.learning.service.launching import MONDAY, retry_program
from app.features.learning.service.proposals import latest_batch, proposal_not_found
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import ResumeRequest, SessionsService, SessionView

logger = logging.getLogger(__name__)

CHOICE_KIND = "choose_path"


def invalid_mix() -> AppError:
    return AppError(
        "invalid_mix", "Un mélange se fait entre deux propositions distinctes du dernier lot.", 422
    )


def proposal_outdated() -> AppError:
    return AppError(
        "proposal_outdated",
        "Cette proposition vient d'un lot précédent : choisis dans le dernier.",
        409,
    )


def council_not_waiting(status: str) -> AppError:
    return AppError(
        "council_not_waiting",
        "Le Conseil n'attend pas de choix pour le moment.",
        409,
        {"status": status},
    )


def check_start_date(start: date | None) -> None:
    """Début du programme : un lundi, aujourd'hui ou plus tard (comme `PATCH /programs`) ;
    sinon 422 `invalid_start_date`, chemin du champ seulement, jamais la valeur."""
    if start is not None and (start.weekday() != MONDAY or start < date.today()):
        raise AppError(
            "invalid_start_date",
            "Un programme commence un lundi, aujourd'hui ou plus tard.",
            422,
            {"fields": ["start_date"]},
        )


async def write_choice(
    db: AsyncSession, user_id: str, session_id: str, goal_id: str, choice: Choice
) -> None:
    """Marque exactement les propositions choisies dans leur lot (les autres du lot ne le sont
    plus) : rejouée, la même écriture ne change rien. Propositions de l'objectif et de la
    session, d'un même lot, sinon 404 / 422."""
    await owned_goal(db, user_id, goal_id)
    repo = ProposalRepository(db, user_id)
    batches: set[int] = set()
    for proposal_id in choice.proposal_ids:
        row = await repo.get_fresh(proposal_id)
        if row is None or row.goal_id != goal_id or row.session_id != session_id:
            raise proposal_not_found()
        batches.add(row.batch)
    if len(batches) != 1:
        raise invalid_mix()
    await repo.set_chosen(session_id, batches.pop(), set(choice.proposal_ids))


def _choice_ids(batch_ids: Sequence[str], proposal_id: str, mix_with: str | None) -> list[str]:
    if proposal_id not in batch_ids:
        raise proposal_outdated()
    if mix_with is None:
        return [proposal_id]
    if mix_with == proposal_id or mix_with not in batch_ids:
        raise invalid_mix()
    return [proposal_id, mix_with]


async def _view(
    runtime: AgentRuntime, learning: LearningRuntime, user_id: str, session_id: str
) -> SessionView:
    async with learning.session_factory() as db:
        return await SessionsService(db, user_id, runtime).get(session_id)


async def _write(
    learning: LearningRuntime, user_id: str, session_id: str, goal_id: str, choice: Choice | None
) -> None:
    """Écrit le choix (ou l'efface, `choice=None`) et commite aussitôt : le nœud `finalize`
    réécrit dans sa propre session."""
    async with learning.session_factory() as db:
        if choice is None:
            batch = await latest_batch(db, user_id, goal_id)
            if batch:
                await ProposalRepository(db, user_id).set_chosen(session_id, batch[0].batch, ())
        else:
            await write_choice(db, user_id, session_id, goal_id, choice)
        await db.commit()


async def _resume(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    user_id: str,
    session_id: str,
    request: ResumeRequest,
) -> SessionView:
    async with learning.session_factory() as db:
        return await SessionsService(db, user_id, runtime).resume(session_id, request)


def _resume_value(choice: Choice) -> dict[str, Any]:
    start = choice.start_date.isoformat() if choice.start_date is not None else None
    return {"action": choice.action, "proposal_ids": list(choice.proposal_ids), "start_date": start}


async def _forget(learning: LearningRuntime, user_id: str, session_id: str, goal_id: str) -> None:
    """Efface le choix écrit, au mieux : un choix resté écrit ne bloque rien (le Conseil qui
    attend encore est toujours repris au clic suivant), il s'afficherait seulement à tort."""
    try:
        await _write(learning, user_id, session_id, goal_id, None)
    except Exception:
        logger.warning(
            "Choix non effacé après une reprise manquée : utilisateur %s, objectif %s",
            user_id,
            goal_id,
        )


async def _write_and_resume(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    user_id: str,
    goal_id: str,
    session_id: str,
    choice: Choice,
    interrupt_id: str,
) -> SessionView:
    """Choix écrit puis interruption reprise. Reprise manquée, pour quelque raison que ce soit
    (question déjà répondue, moteur en arrêt, base verrouillée, arrêt du back) : choix effacé,
    `finalize` écrira celui qu'il recevra ; une question déjà répondue donne 409
    `council_not_waiting` avec le statut relu après l'échec."""
    await _write(learning, user_id, session_id, goal_id, choice)
    request = ResumeRequest(interrupt_id=interrupt_id, value=_resume_value(choice))
    try:
        return await _resume(runtime, learning, user_id, session_id, request)
    except BaseException as exc:
        await _forget(learning, user_id, session_id, goal_id)
        if isinstance(exc, AppError) and exc.code == "stale_interrupt":
            status = (await _view(runtime, learning, user_id, session_id)).status
            raise council_not_waiting(status) from None
        raise


async def choose(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    db: AsyncSession,
    user_id: str,
    proposal_id: str,
    req: ChooseRequest,
) -> ChooseOut:
    """Sous le verrou de l'objectif : (1) proposition (et `mix_with`) du dernier lot ; (2) Conseil
    en attente sur `choose_path` → choix écrit puis interruption reprise, **toujours** (un choix
    resté écrit par une reprise manquée ne bloque pas) ; (3) Conseil qui n'attend pas : même
    ensemble déjà choisi → Stratège relancé s'il a échoué sans programme (`retry_program`,
    `already_chosen` faux), sinon état rendu, `already_chosen` vrai, rien changé (`start_date`
    comprise ; double clic, reprise générique terminée) ; autre ensemble : 409
    `council_not_waiting`. `start_date` : un lundi à venir, sinon 422 `invalid_start_date`."""
    check_start_date(req.start_date)
    goal_id = await ProposalRepository(db, user_id).goal_of(proposal_id)
    if goal_id is None:
        raise proposal_not_found()
    async with learning.goal_lock(user_id, goal_id):
        async with learning.session_factory() as fresh:
            batch = await latest_batch(fresh, user_id, goal_id)
        ids = _choice_ids([p.id for p in batch], proposal_id, req.mix_with)
        session_id = batch[0].session_id
        view = await _view(runtime, learning, user_id, session_id)
        pending = view.pending_interrupt
        if view.status != "waiting_user" or pending is None or pending.kind != CHOICE_KIND:
            if {p.id for p in batch if p.chosen} != set(ids):
                raise council_not_waiting(view.status)
            retried = await retry_program(
                learning, user_id, goal_id, view.status, ids, req.start_date
            )
            return ChooseOut(
                council_session_id=session_id, status=view.status, already_chosen=retried is None
            )
        action: Literal["choose", "mix"] = "mix" if len(ids) == 2 else "choose"
        choice = Choice(action, tuple(ids), req.start_date)
        resumed = await _write_and_resume(
            runtime, learning, user_id, goal_id, session_id, choice, pending.interrupt_id
        )
    logger.info(
        "Parcours choisi par la route : utilisateur %s, objectif %s, Conseil %s, propositions %s",
        user_id,
        goal_id,
        session_id,
        ",".join(ids),
    )
    return ChooseOut(council_session_id=session_id, status=resumed.status)
