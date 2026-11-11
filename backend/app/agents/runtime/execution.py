"""Exécution d'une session : compile le parcours, parcourt `astream`, publie les événements, puis
écrit l'issue (question en attente, fin, échec).

- `durability="sync"` : le checkpoint d'une étape est écrit avant l'étape suivante ; un arrêt
  brutal ne fait jamais rejouer un nœud terminé (Review Focus 1).
- Chaque issue est une transition conditionnelle depuis `running`, écrite dans la MÊME
  transaction que son événement (`EventBus.publish_with`, D61) : statut et événement existent
  ensemble ou pas du tout. Si la session a été mise en pause ou annulée entre-temps, rien
  n'est écrit ni publié.
- Écriture de l'issue en échec (D61 §4) : nouveaux essais (la garde les rend sûrs), puis repli
  sur un `failed` atomique (`outcome_not_written`), pour ne jamais laisser une session
  `running` sans tâche dans le processus. Si même le repli échoue (base vraiment
  indisponible), la session reste `running` et sera reprise au prochain démarrage.
- L'issue s'écrit en entier même si la tâche est annulée à ce moment (`_settle`).
- `bus.close` seulement si la session est en base dans un statut terminal (et `cancelled`, par
  le runner) ; jamais sur `waiting_user` ni `paused` (D42), ni sur une issue non écrite (la
  session reste ouverte : un 1000 serait pris pour une fin définitive, D50).
"""

import asyncio
import logging
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.pregel import Pregel
from langgraph.types import Command, StreamMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GraphSpec
from app.agents.runtime.bus import EventBus, Guard
from app.agents.runtime.checkpointer import thread_config
from app.agents.runtime.control import TERMINAL
from app.agents.runtime.costs import CostTracker, ModelPrice
from app.agents.runtime.deps import ChatModelSource, GraphDeps
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.runtime.stream import translate_chunk
from app.agents.tools.memory_port import NO_MEMORY, MemoryGateway
from app.core.errors import AppError

logger = logging.getLogger(__name__)

STREAM_MODES: list[StreamMode] = ["custom", "messages", "updates"]
INTERNAL_ERROR = "Une erreur inattendue a interrompu la session."
NOT_WRITTEN = {
    "code": "outcome_not_written",
    "message": "La fin de la session n'a pas pu être enregistrée : elle est marquée en échec.",
}
# Attente avant chaque nouvel essai d'écriture de l'issue (deux nouveaux essais).
OUTCOME_RETRY_DELAYS_S = (0.05, 0.25)


@dataclass(frozen=True)
class RunContext:
    session_factory: async_sessionmaker[AsyncSession]
    bus: EventBus
    models: ChatModelSource
    checkpointer: BaseCheckpointSaver[Any]
    prices: Mapping[str, ModelPrice]
    graphs: Mapping[str, GraphSpec]
    run_settings: RunSettingsSource
    memory: MemoryGateway = NO_MEMORY


def unknown_graph(name: str) -> AppError:
    return AppError("unknown_graph", f"Parcours inconnu : {name}", 404, {"graph": name})


async def run_session(
    ctx: RunContext, user_id: str, session_id: str, command: Command[Any] | None
) -> None:
    """Corps de la tâche d'une session. `command` : réponse à une question, ou `None` (départ,
    reprise d'une pause ou après redémarrage : dernier checkpoint, à défaut l'entrée).

    `CancelledError` est relancée sans rien écrire : le statut appartient à l'appelant (pause,
    annulation) ou reste `running` (arrêt du serveur, la session sera reprise au démarrage).
    """
    run = _Run(ctx, user_id, session_id)
    try:
        prepared = await run.prepare(command)
        if prepared is None:
            return  # plus `running` (pause, annulation passées avant) : rien à faire ni écrire
        graph, config, graph_input = prepared
        pending = await run.stream(graph, graph_input, config)
        if pending is not None:
            outcome = run.wait_user(pending)
        else:
            outcome = run.complete(await _summary(graph, session_id))
    except asyncio.CancelledError:
        raise
    except AppError as exc:
        outcome = run.fail(exc.code, exc.message)
    except Exception as exc:  # message brut jamais journalisé ni publié (clés, données)
        logger.error(
            "Session %s (utilisateur %s) : échec inattendu (%s)",
            session_id,
            user_id,
            type(exc).__name__,
        )
        outcome = run.fail("internal_error", INTERNAL_ERROR)
    await _settle(outcome)


async def _settle(outcome: Awaitable[None]) -> None:
    """Écrit l'issue jusqu'au bout même si la tâche est annulée pendant, puis laisse
    l'annulation suivre son cours : un statut écrit sans son événement n'arrive jamais."""
    task = asyncio.ensure_future(outcome)
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.wait({task})
        if not task.cancelled() and (error := task.exception()) is not None:
            logger.error("Issue d'une session non écrite (%s)", type(error).__name__)
        raise


async def _summary(graph: Pregel[Any, Any, Any, Any], session_id: str) -> str:
    values = (await graph.aget_state(thread_config(session_id))).values
    summary = values.get("summary") if isinstance(values, dict) else None
    return summary if isinstance(summary, str) else ""


class _Run:
    def __init__(self, ctx: RunContext, user_id: str, session_id: str) -> None:
        self.ctx = ctx
        self.user_id = user_id
        self.session_id = session_id

    async def prepare(
        self, command: Command[Any] | None
    ) -> tuple[Pregel[Any, Any, Any, Any], RunnableConfig, Any] | None:
        """Graphe compilé, configuration et entrée ; `None` si la session n'est plus
        `running` (une pause ou une annulation est passée avant le démarrage de la tâche)."""
        ctx = self.ctx
        async with ctx.session_factory() as db:
            row = await SessionRepository(db, self.user_id).get(self.session_id)
        if row is None:
            raise AppError("session_not_found", "Session introuvable.", 404)
        if row.status != "running":
            return None
        settings = await ctx.run_settings.get_run_settings(self.user_id)
        spec = ctx.graphs.get(row.graph)
        if spec is None:
            raise unknown_graph(row.graph)
        deps = GraphDeps(
            self.user_id,
            self.session_id,
            ctx.models,
            ctx.bus,
            settings,
            ctx.session_factory,
            ctx.memory,
        )
        graph = spec.build(deps).compile(checkpointer=ctx.checkpointer)
        tracker = CostTracker(
            user_id=self.user_id,
            session_id=self.session_id,
            graph=row.graph,
            bus=ctx.bus,
            session_factory=ctx.session_factory,
            prices=ctx.prices,
            cap_tokens=settings.session_token_cap,
        )
        config: RunnableConfig = {**thread_config(self.session_id), "callbacks": [tracker]}
        graph_input: Any = command
        if command is None and await ctx.checkpointer.aget_tuple(config) is None:
            graph_input = row.input  # aucun checkpoint : (re)départ depuis l'entrée
        return graph, config, graph_input

    async def stream(
        self, graph: Pregel[Any, Any, Any, Any], graph_input: Any, config: RunnableConfig
    ) -> dict[str, Any] | None:
        """Publie le flux ; rend la première question posée (une à la fois : les autres
        interruptions en attente reviendront à la reprise, avec le même id)."""
        pending: dict[str, Any] | None = None
        async for mode, chunk in graph.astream(
            graph_input, config, stream_mode=STREAM_MODES, durability="sync"
        ):
            for event in translate_chunk(mode, chunk):
                if event.type == "interrupt.requested":
                    pending = pending or event.payload
                    continue
                await self.publish(event.type, event.payload, event.agent)
        return pending

    async def publish(self, type: Any, payload: dict[str, Any], agent: str | None = None) -> None:
        await self.ctx.bus.publish(
            user_id=self.user_id,
            session_id=self.session_id,
            type=type,
            payload=payload,
            agent=agent,
        )

    def _guard(self, to: str, **values: Any) -> Guard:
        async def guard(db: AsyncSession) -> bool:
            return await SessionRepository(db, self.user_id).transition(
                self.session_id, from_={"running"}, to=to, **values
            )

        return guard

    async def _outcome(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> bool:
        """Statut `to` (depuis `running`) et événement `event_type` validés ensemble (D61) ; `False`
        si la session n'est plus `running` (pause, annulation) : rien d'écrit ni de publié."""
        event = await self.ctx.bus.publish_with(
            user_id=self.user_id,
            session_id=self.session_id,
            type=event_type,
            payload=payload,
            guard=self._guard(to, **values),
        )
        return event is not None

    async def wait_user(self, pending: dict[str, Any]) -> None:
        # Question et statut ensemble : qui reçoit la question peut y répondre aussitôt.
        await self._issue("waiting_user", "interrupt.requested", pending, pending_interrupt=pending)

    async def complete(self, summary: str) -> None:
        await self._issue("completed", "run.completed", {"summary": summary}, error=None)

    async def fail(self, code: str, message: str) -> None:
        error = {"code": code, "message": message}
        await self._issue("failed", "run.failed", error, error=error)

    async def _issue(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> None:
        """Écrit l'issue (nouveaux essais), à défaut un `failed` `outcome_not_written` ; lève si
        rien ne s'écrit (la session reste `running`). Puis `bus.close` si la session est en
        base dans un statut terminal : les abonnés reçoivent l'événement final et s'arrêtent."""
        try:
            written = await self._persist(to, event_type, payload, **values)
        except Exception as exc:
            logger.error(
                "Session %s : issue « %s » non écrite (%s), repli en échec",
                self.session_id,
                to,
                type(exc).__name__,
            )
            to = "failed"
            written = await self._persist(to, "run.failed", NOT_WRITTEN, error=NOT_WRITTEN)
        # Refusée : pause, annulation, ou un essai précédent a validé malgré son erreur.
        final = to in TERMINAL if written else await self._status() in TERMINAL
        if final:
            await self.ctx.bus.close(user_id=self.user_id, session_id=self.session_id)

    async def _persist(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> bool:
        """`_outcome` avec nouveaux essais sur erreur (base occupée au-delà du délai d'attente).
        Sûr : si un essai a validé malgré son erreur, la garde refuse le suivant."""
        for delay in OUTCOME_RETRY_DELAYS_S:
            try:
                return await self._outcome(to, event_type, payload, **values)
            except Exception as exc:
                logger.warning(
                    "Session %s : écriture de l'issue en échec (%s), nouvel essai",
                    self.session_id,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
        return await self._outcome(to, event_type, payload, **values)

    async def _status(self) -> str | None:
        async with self.ctx.session_factory() as db:
            row = await SessionRepository(db, self.user_id).get(self.session_id)
        return None if row is None else row.status
