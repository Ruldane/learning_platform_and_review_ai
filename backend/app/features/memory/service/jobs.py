"""Worker de la mémoire : une seule tâche asyncio par processus, une file en mémoire, des jobs
exécutés un par un (D66). Au démarrage, les documents `queued` et `processing` (import coupé par
un arrêt) sont remis en file. Une exception ne tue jamais la boucle ; chaque job a un délai.

La file n'est pas persistée : c'est l'état des documents en base qui fait foi, relu au démarrage.
Les journaux ne citent que des identifiants et des types d'exception."""

import asyncio
import logging
from collections.abc import Callable

from app.features.memory.repository import list_documents_to_resume
from app.features.memory.service.pipeline import FAILED, ingest, mark_error
from app.features.memory.service.runtime import MemoryRuntime

logger = logging.getLogger(__name__)

JOB_TIMEOUT_S: float = 300
TIMEOUT_ERROR = {"code": "ingestion_timeout", "message": "L'import a dépassé 5 minutes."}


class MemoryJobs:
    def __init__(self, runtime_factory: Callable[[], MemoryRuntime]) -> None:
        # Fabrique : le runtime contient ce worker, il n'existe donc qu'après lui.
        self._runtime_factory = runtime_factory
        self._queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Relit les documents à reprendre, les met en file et lance UNE tâche worker."""
        if self._worker is not None:
            return
        runtime = self._runtime_factory()
        async with runtime.session_factory() as db:
            pending = await list_documents_to_resume(db)
        for user_id, document_id in pending:
            self.enqueue_ingest(user_id, document_id)
        if pending:
            logger.info("%d document(s) remis en file au démarrage", len(pending))
        self._worker = asyncio.create_task(self._loop(), name="memory-jobs")

    def enqueue_ingest(self, user_id: str, document_id: str) -> None:
        """Après le commit du document. Mettre deux fois le même document en file est sans
        effet : le second passage le trouve déjà `indexed` ou `error`."""
        self._queue.put_nowait((user_id, document_id))

    async def join(self) -> None:
        """Pour les tests : attend que la file soit vide et le worker au repos."""
        await self._queue.join()

    async def aclose(self) -> None:
        """Annule le worker et attend sa fin. Le document en cours reste `processing` : il
        repartira au prochain démarrage. Idempotent."""
        worker, self._worker = self._worker, None
        if worker is None:
            return
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise

    async def _loop(self) -> None:
        while True:
            user_id, document_id = await self._queue.get()
            try:
                await self._execute(user_id, document_id)
            except Exception as exc:
                logger.error("Job du document %s abandonné (%s)", document_id, type(exc).__name__)
            finally:
                self._queue.task_done()

    async def _execute(self, user_id: str, document_id: str) -> None:
        runtime = self._runtime_factory()
        try:
            async with asyncio.timeout(JOB_TIMEOUT_S):
                await ingest(runtime, user_id, document_id)
            return
        except TimeoutError:
            logger.warning("Import du document %s : délai dépassé", document_id)
            error = TIMEOUT_ERROR
        except Exception as exc:
            logger.warning("Import du document %s en échec (%s)", document_id, type(exc).__name__)
            error = FAILED
        await mark_error(runtime, user_id, document_id, error)
