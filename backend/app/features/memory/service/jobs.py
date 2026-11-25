"""Memory worker: a single asyncio task per process, an in-memory queue, jobs run one by one
(D66): document imports and reindexings (D67). At startup, `queued` and `processing` documents
(import cut by a stop) are put back in the queue. An exception never kills the loop; each job
has a timeout.

The queue is not persisted: the state of the documents in the database is authoritative, re-read
at startup. The state of a reindexing lives in memory and is lost on restart; this is harmless,
the items it did not process keep a null `indexed_at` and the next one catches them up.
Logs only quote ids and exception types."""

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
TIMEOUT_ERROR = {"code": "ingestion_timeout", "message": "The import took longer than 5 minutes."}
REINDEX_TIMEOUT_S: float = 3600
REINDEX_TIMEOUT = "Reindexing took longer than an hour."
REINDEX_FAILED = "Reindexing failed unexpectedly."
IDLE = ReindexState(status="idle", done=0, total=0, error=None)


class MemoryJobs:
    def __init__(self, runtime_factory: Callable[[], MemoryRuntime]) -> None:
        # Factory: the runtime contains this worker, so it only exists after it.
        self._runtime_factory = runtime_factory
        # (user, document); document `None`: reindexing of the user.
        self._queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._scheduled: Counter[str] = Counter()  # documents queued or running
        self._reindex: dict[str, ReindexState] = {}

    async def start(self) -> None:
        """Re-reads the documents to resume, queues them and starts ONE worker task."""
        if self._worker is not None:
            return
        runtime = self._runtime_factory()
        async with runtime.session_factory() as db:
            pending = await list_documents_to_resume(db)
        for user_id, document_id in pending:
            self.enqueue_ingest(user_id, document_id)
        if pending:
            logger.info("%d document(s) put back in the queue at startup", len(pending))
        self._worker = asyncio.create_task(self._loop(), name="memory-jobs")

    def enqueue_ingest(self, user_id: str, document_id: str) -> None:
        """After the document's commit. Queueing the same document twice has no effect: the
        second pass finds it already `indexed` or `error`."""
        self._scheduled[document_id] += 1
        self._queue.put_nowait((user_id, document_id))

    def enqueue_reindex(self, user_id: str) -> ReindexState:
        """Queues the user's reindexing. Already queued or running: returns the current state,
        without a second job (a double click never launches two reindexings)."""
        current = self.reindex_state(user_id)
        if current.status in ("queued", "running"):
            return current
        queued = ReindexState(status="queued", done=0, total=0, error=None)
        self._reindex[user_id] = queued
        self._queue.put_nowait((user_id, None))
        return queued

    def reindex_state(self, user_id: str) -> ReindexState:
        """State of the user's last reindexing; `idle` if there has been none since
        startup."""
        return self._reindex.get(user_id, IDLE)

    def is_scheduled(self, document_id: str) -> bool:
        """True if the document is waiting in the queue or being processed."""
        return self._scheduled[document_id] > 0

    async def join(self) -> None:
        """For tests: waits for the queue to be empty and the worker idle."""
        await self._queue.join()

    async def aclose(self) -> None:
        """Cancels the worker and waits for it to end. The document in progress stays
        `processing`: it will restart at the next startup. Idempotent."""
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
                logger.error("Job of %s abandoned (%s)", document_id or user_id, type(exc).__name__)
            finally:
                if document_id is not None:
                    self._scheduled[document_id] -= 1
                    if self._scheduled[document_id] <= 0:
                        del self._scheduled[document_id]
                self._queue.task_done()

    async def _reindex_job(self, user_id: str) -> None:
        """Reindexing: `running`, then `done` or `failed` with a readable message (the port's for
        an Ollama or Qdrant outage, never the text of another exception)."""

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
        logger.warning("Reindexing of %s failed (%s)", user_id, cause)
        report(state.model_copy(update={"status": "failed", "error": error}))

    async def _execute(self, user_id: str, document_id: str) -> None:
        runtime = self._runtime_factory()
        try:
            async with asyncio.timeout(JOB_TIMEOUT_S):
                await ingest(runtime, user_id, document_id)
            return
        except TimeoutError:
            logger.warning("Import of document %s: timed out", document_id)
            error = TIMEOUT_ERROR
        except Exception as exc:
            logger.warning("Import of document %s failed (%s)", document_id, type(exc).__name__)
            error = FAILED
        await mark_error(runtime, user_id, document_id, error)
