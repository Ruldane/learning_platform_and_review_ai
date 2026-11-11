"""Règles de statut d'une session : reprise, pause, annulation, messages (SPEC 13.2, D3).

Chaque changement de statut est une transition conditionnelle en base
(`SessionRepository.transition`) : deux demandes concurrentes (double clic sur une réponse,
pause pendant que le graphe se termine) ne peuvent pas réussir toutes les deux. Le runner décide
ensuite quoi faire de la tâche ; ce module ne touche qu'à la base.
"""

from collections.abc import Collection
from typing import Any

from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import SessionRepository
from app.core.errors import AppError
from app.db.models.agents import AgentSession

TERMINAL = frozenset({"completed", "failed", "cancelled"})
OPEN = frozenset({"running", "waiting_user", "paused"})  # reçoit des messages, annulable
PAUSABLE = frozenset({"running", "waiting_user"})

type Factory = async_sessionmaker[AsyncSession]


def _conflict(code: str, message: str, status: str) -> AppError:
    return AppError(code, message, 409, {"status": status})


def stale_interrupt(status: str) -> AppError:
    return _conflict("stale_interrupt", "Cette question a déjà reçu une réponse.", status)


async def get_owned(db: Factory, user_id: str, session_id: str) -> AgentSession:
    """La session de `user_id` ; 404 si elle n'existe pas ou appartient à un autre."""
    async with db() as session:
        row = await SessionRepository(session, user_id).get(session_id)
    if row is None:
        raise AppError("session_not_found", "Session introuvable.", 404)
    return row


async def transition(
    db: Factory,
    user_id: str,
    session_id: str,
    *,
    from_: Collection[str],
    to: str,
    **values: Any,
) -> bool:
    async with db() as session:
        done = await SessionRepository(session, user_id).transition(
            session_id, from_=from_, to=to, **values
        )
        await session.commit()
    return done


async def claim_resume(
    db: Factory, user_id: str, session_id: str, interrupt_id: str | None, value: Any
) -> Command[Any] | None:
    """Passe la session à `running` (question effacée) et rend l'entrée du graphe : la réponse
    adressée à l'interruption par son id, ou `None` (reprise d'une pause sur le dernier
    checkpoint). 409 lisible si la question est périmée ou la session pas en attente."""
    row = await get_owned(db, user_id, session_id)
    if row.status == "waiting_user" and interrupt_id is not None:
        pending = (row.pending_interrupt or {}).get("interrupt_id")
        if interrupt_id != pending or not await transition(
            db, user_id, session_id, from_={"waiting_user"}, to="running", pending_interrupt=None
        ):
            raise stale_interrupt(row.status)
        # Forme « carte » : la réponse va à cette interruption-là, même s'il y en a d'autres.
        return Command(resume={interrupt_id: value})
    if row.status == "paused" and interrupt_id is None:
        if not await transition(db, user_id, session_id, from_={"paused"}, to="running"):
            raise _not_resumable(row.status)
        return None
    if interrupt_id is not None:
        raise stale_interrupt(row.status)  # déjà répondue, ou session plus en attente
    if row.status == "waiting_user":
        raise _conflict(
            "interrupt_required", "Cette session attend une réponse à sa question.", row.status
        )
    raise _not_resumable(row.status)


def _not_resumable(status: str) -> AppError:
    return _conflict(
        "session_not_resumable", "Cette session ne peut pas être reprise dans son état.", status
    )


async def claim_pause(db: Factory, user_id: str, session_id: str) -> bool:
    """`True` si la session vient de passer en pause, `False` si elle l'était déjà ; 409 si
    elle est terminée. La question en attente est effacée : la reprise la reposera."""
    row = await get_owned(db, user_id, session_id)
    if row.status == "paused":
        return False
    if not await transition(
        db, user_id, session_id, from_=PAUSABLE, to="paused", pending_interrupt=None
    ):
        status = (await get_owned(db, user_id, session_id)).status
        if status == "paused":
            return False
        raise _conflict(
            "session_not_pausable", "Cette session est terminée : pas de pause possible.", status
        )
    return True


async def claim_cancel(db: Factory, user_id: str, session_id: str) -> None:
    await get_owned(db, user_id, session_id)  # 404 avant 409
    if not await transition(
        db, user_id, session_id, from_=OPEN, to="cancelled", pending_interrupt=None
    ):
        status = (await get_owned(db, user_id, session_id)).status
        raise _conflict("session_not_cancellable", "Cette session est déjà terminée.", status)


async def check_open(db: Factory, user_id: str, session_id: str) -> None:
    """Une session terminée ne reçoit plus de message (409)."""
    row = await get_owned(db, user_id, session_id)
    if row.status not in OPEN:
        raise _conflict(
            "session_closed",
            "Cette session est terminée : elle ne reçoit plus de message.",
            row.status,
        )
