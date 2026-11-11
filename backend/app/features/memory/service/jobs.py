"""Worker de la mémoire : une seule tâche asyncio par processus, une file en mémoire, des jobs
exécutés un par un (D66) : imports de documents et réindexations (D67). Au démarrage, les
documents `queued` et `processing` (import coupé par un arrêt) sont remis en file. Une exception
ne tue jamais la boucle ; chaque job a un délai.

La file n'est pas persistée : c'est l'état des documents en base qui fait foi, relu au démarrage.
L'état d'une réindexation vit en mémoire et se perd au redémarrage ; c'est sans danger, les
éléments qu'elle n'a pas traités gardent `indexed_at` nul et la suivante les rattrape.
Les journaux ne citent que des identifiants et des types d'exception."""

import asyncio
import logging
from collections import Counter
from collections.abc import Callable

from app.core.errors import AppError
from app.features.memory.repository import list_documents_to_resume
from app.features.memory.schemas import ReindexState
from app.features.memory.service.pipeline import FAILED, ingest, mark_error
from app.features.memory.service.reindex import reindex_user
from app.features.memory.service.runtime import MemoryRuntime

logger = logging.getLogger(__name__)

JOB_TIMEOUT_S: float = 300
TIMEOUT_ERROR = {"code": "ingestion_timeout", "message": "L'import a dépassé 5 minutes."}
REINDEX_TIMEOUT_S: float = 3600
REINDEX_TIMEOUT = "La réindexation a dépassé une heure."
REINDEX_FAILED = "La réindexation a échoué de façon inattendue."
IDLE = ReindexState(status="idle", done=0, total=0, error=None)


class MemoryJobs:
    def __init__(self, runtime_factory: Callable[[], MemoryRuntime]) -> None:
        # Fabrique : le runtime contient ce worker, il n'existe donc qu'après lui.
        self._runtime_factory = runtime_factory
        # (utilisateur, document) ; document `None` : réindexation de l'utilisateur.
        self._queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._scheduled: Counter[str] = Counter()  # documents en file ou en cours
        self._reindex: dict[str, ReindexState] = {}

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
        self._scheduled[document_id] += 1
        self._queue.put_nowait((user_id, document_id))

    def enqueue_reindex(self, user_id: str) -> ReindexState:
        """Met la réindexation de l'utilisateur en file. Déjà en file ou en cours : rend l'état
        courant, sans second job (un double clic ne lance jamais deux réindexations)."""
        current = self.reindex_state(user_id)
        if current.status in ("queued", "running"):
            return current
        queued = ReindexState(status="queued", done=0, total=0, error=None)
        self._reindex[user_id] = queued
        self._queue.put_nowait((user_id, None))
        return queued

    def reindex_state(self, user_id: str) -> ReindexState:
        """État de la dernière réindexation de l'utilisateur ; `idle` s'il n'y en a pas eu
        depuis le démarrage."""
        return self._reindex.get(user_id, IDLE)

    def is_scheduled(self, document_id: str) -> bool:
        """Vrai si le document attend dans la file ou est en cours de traitement."""
        return self._scheduled[document_id] > 0

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
                if document_id is None:
                    await self._reindex_job(user_id)
                else:
                    await self._execute(user_id, document_id)
            except Exception as exc:
                logger.error("Job de %s abandonné (%s)", document_id or user_id, type(exc).__name__)
            finally:
                if document_id is not None:
                    self._scheduled[document_id] -= 1
                    if self._scheduled[document_id] <= 0:
                        del self._scheduled[document_id]
                self._queue.task_done()

    async def _reindex_job(self, user_id: str) -> None:
        """Réindexation : `running`, puis `done` ou `failed` avec un message lisible (celui du
        port pour une panne d'Ollama ou de Qdrant, jamais le texte d'une autre exception)."""

        def report(state: ReindexState) -> None:
            self._reindex[user_id] = state

        report(ReindexState(status="running", done=0, total=0, error=None))
        try:
            async with asyncio.timeout(REINDEX_TIMEOUT_S):
                await reindex_user(self._runtime_factory(), user_id, report)
            return
        except AppError as exc:
            error, cause = exc.message, exc.code
        except TimeoutError:
            error, cause = REINDEX_TIMEOUT, "timeout"
        except Exception as exc:
            error, cause = REINDEX_FAILED, type(exc).__name__
        state = self.reindex_state(user_id)
        logger.warning("Réindexation de %s en échec (%s)", user_id, cause)
        report(state.model_copy(update={"status": "failed", "error": error}))

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
