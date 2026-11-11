"""`SessionRunner` : lance, reprend, met en pause, annule les sessions et reprend celles qu'un
arrêt du serveur a interrompues. Une tâche asyncio par session active, toujours suivie : aucune
n'est orpheline, `shutdown` les annule et les attend.

Le corps d'une tâche vit dans `execution.py`, les règles de statut dans `control.py`.
"""

import asyncio
import logging
from collections.abc import Mapping
from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.runtime import control
from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.events import SessionEvent
from app.agents.runtime.execution import RunContext, run_session, unknown_graph
from app.agents.runtime.repositories import SessionRepository, list_sessions_to_recover
from app.core.errors import AppError
from app.db.models.agents import AgentSession

logger = logging.getLogger(__name__)


class SessionRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        bus: EventBus,
        models: ChatModelSource,
        checkpointer: BaseCheckpointSaver[Any],
        prices: Mapping[str, ModelPrice],
        graphs: Mapping[str, GraphSpec] = GRAPHS,
    ) -> None:
        self._db = session_factory
        self._bus = bus
        self._ctx = RunContext(session_factory, bus, models, checkpointer, prices, graphs)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._stopping = False

    # --- Démarrage et reprise ------------------------------------------------------------

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str:
        """Valide l'entrée, crée la session `running`, lance sa tâche et rend la main aussitôt."""
        spec = self._ctx.graphs.get(graph)
        if spec is None:
            raise unknown_graph(graph)
        try:
            data = spec.input_model.model_validate(input).model_dump(mode="json")
        except ValidationError as exc:  # chemins des champs seulement, jamais les valeurs
            fields = [".".join(str(p) for p in err["loc"]) for err in exc.errors()]
            raise AppError(
                "invalid_input", "L'entrée du parcours est invalide.", 422, {"fields": fields}
            ) from None
        async with self._db() as db:
            row = await SessionRepository(db, user_id).add(
                graph=graph,
                status="running",
                input=data,
                subject_type=subject_type,
                subject_id=subject_id,
            )
            await db.commit()
        self._launch(user_id, row.id, None)
        return row.id

    async def resume(
        self, user_id: str, session_id: str, interrupt_id: str | None, value: Any
    ) -> None:
        """Réponse à la question en attente (`interrupt_id` = celui de `pending_interrupt`), ou
        reprise d'une pause (`interrupt_id=None`) sur le dernier checkpoint."""
        command = await control.claim_resume(self._db, user_id, session_id, interrupt_id, value)
        await self._settle(session_id)  # la tâche qui a posé la question finit d'en publier
        self._launch(user_id, session_id, command)

    async def recover_on_startup(self) -> list[str]:
        """Relance les sessions `running` qu'un arrêt a interrompues (dernier checkpoint : aucun
        nœud terminé ne rejoue). `waiting_user` et `paused` attendent l'utilisatrice."""
        async with self._db() as db:
            to_recover = await list_sessions_to_recover(db)
        for user_id, session_id in to_recover:
            self._launch(user_id, session_id, None)
        return [session_id for _, session_id in to_recover]

    # --- Actions de l'utilisatrice -------------------------------------------------------

    async def post_message(self, user_id: str, session_id: str, text: str) -> SessionEvent:
        """Publie `user.message` ; les nœuds le lisent au tour suivant
        (`GraphDeps.user_messages_since`, D4)."""
        await control.check_open(self._db, user_id, session_id)
        return await self._bus.publish(
            user_id=user_id, session_id=session_id, type="user.message", payload={"text": text}
        )

    async def pause(self, user_id: str, session_id: str) -> AgentSession:
        if await control.claim_pause(self._db, user_id, session_id):
            await self._stop(session_id)
        return await control.get_owned(self._db, user_id, session_id)

    async def cancel(self, user_id: str, session_id: str) -> AgentSession:
        await control.claim_cancel(self._db, user_id, session_id)
        await self._stop(session_id)
        await self._bus.close(user_id=user_id, session_id=session_id)
        return await control.get_owned(self._db, user_id, session_id)

    # --- Tâches --------------------------------------------------------------------------

    def is_active(self, session_id: str) -> bool:
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    async def shutdown(self) -> None:
        """Arrêt du serveur : annule et attend toutes les tâches SANS changer leur statut (les
        sessions `running` seront reprises au prochain démarrage)."""
        self._stopping = True
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _launch(self, user_id: str, session_id: str, command: Command[Any] | None) -> None:
        if self._stopping:
            raise AppError(
                "server_stopping", "Le serveur s'arrête : réessaie dans un instant.", 503
            )
        task = asyncio.create_task(
            run_session(self._ctx, user_id, session_id, command), name=f"session:{session_id}"
        )
        self._tasks[session_id] = task
        task.add_done_callback(partial(self._forget, session_id))

    def _forget(self, session_id: str, task: asyncio.Task[None]) -> None:
        if self._tasks.get(session_id) is task:
            del self._tasks[session_id]
        if not task.cancelled() and task.exception() is not None:
            # Issue impossible à écrire (base indisponible) : la session reste `running` et sera
            # reprise au prochain démarrage.
            logger.error(
                "Session %s : issue non écrite (%s)", session_id, type(task.exception()).__name__
            )

    async def _settle(self, session_id: str) -> None:
        """Attend la fin de la tâche en cours, sans l'annuler."""
        task = self._tasks.get(session_id)
        if task is not None:
            await asyncio.wait({task})

    async def _stop(self, session_id: str) -> None:
        """Annule la tâche en cours et attend qu'elle soit finie."""
        task = self._tasks.get(session_id)
        if task is not None:
            task.cancel()
            await asyncio.wait({task})
