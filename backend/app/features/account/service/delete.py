"""The "Delete everything" flow (P19): the order is the one that can be replayed to the end.

No session of the account starts or resumes any more (engine guard, lifted at the end, whether
it succeeded or not), active sessions are cancelled, then vectors, files, session checkpoints,
and finally the rows of **every** table with `user_id` (`all_user_tables`) in a single
transaction, children first. Cancellation is repeated just before reading the threads: no
session outlives the account. Each step is idempotent and the database only changes at the end:
an interrupted call (Qdrant down, locked disk) is redone in full, and nothing is deleted from
the database until the vectors, files and checkpoints are. A final purge removes any vectors
from an in-flight `indexer.push`. For a Google account, the transaction records this purge under
the old id, so it can be resumed without a session.
After `ROUNDS` cancellation rounds without success: 503 `account_busy`, before any write.

Same per-account lock as the export: the two never overlap. Logs only carry the id, numbers
and the duration.
"""

import logging
import time
from typing import Any, Literal, cast

from sqlalchemy import delete
from sqlalchemy.engine import CursorResult

from app.core.errors import AppError
from app.db.base import Base
from app.db.models.accounts import AccountVectorPurge
from app.features.account.repository import AccountRepository, queue_vector_purge
from app.features.account.service.export import export_lock
from app.features.account.service.runtime import AccountRuntime
from app.features.account.service.tables import all_user_tables
from app.features.account.service.vector_purges import finish_vector_purge
from app.providers.vector.base import VectorStoreUnavailable

logger = logging.getLogger(__name__)

NOT_CANCELLABLE = "session_not_cancellable"  # finished between the read and the cancellation
ROUNDS = 5  # at most this many cancellation rounds: the guard stops new ones, this is a net
_SESSIONS = Base.metadata.tables["sessions"]


async def _session_ids(rt: AccountRuntime, user_id: str) -> list[str]:
    async with rt.session_factory() as db:
        rows = await AccountRepository(db, user_id).rows(_SESSIONS, [_SESSIONS.c.id])
    return [row["id"] for row in rows]


async def _cancel_open_sessions(rt: AccountRuntime, user_id: str) -> int:
    """Cancels `running`, `waiting_user` and `paused` sessions: no task writes to the database
    or the account's checkpoints any more. Re-reads the open sessions and starts again until
    none is left (a session born in the meantime is caught). A session that just finished is
    left alone."""
    cancelled = 0
    for _ in range(ROUNDS):
        open_ids = await rt.runtime.open_sessions(user_id)
        if not open_ids:
            return cancelled
        for session_id in open_ids:
            try:
                await rt.runtime.cancel(user_id, session_id)
                cancelled += 1
            except AppError as exc:
                if exc.code != NOT_CANCELLABLE:
                    raise
    raise AppError(
        "account_busy",
        "Some of the account's sessions will not stop: nothing was deleted, try again.",
        503,
    )


async def _delete_vectors(rt: AccountRuntime, user_id: str, *, rows_deleted: bool = False) -> None:
    try:
        await rt.index.delete_user(user_id)
    except VectorStoreUnavailable:
        if rows_deleted:
            raise AppError(
                "vector_purge_incomplete",
                "Your data is erased from the database. The vector purge still has to finish.",
                503,
            ) from None
        raise AppError(
            "vector_store_unavailable",
            "The vector store is unavailable: nothing was deleted, try again.",
            503,
        ) from None


async def _delete_files(rt: AccountRuntime, user_id: str) -> int:
    try:
        return await rt.storage.delete_user(user_id)
    except OSError:  # file open elsewhere (Windows), locked disk: replaying is safe
        raise AppError(
            "storage_unavailable",
            "Some files are locked: nothing was deleted, try again.",
            503,
        ) from None


async def _delete_rows(rt: AccountRuntime, user_id: str, *, keep_user: bool) -> tuple[int, int]:
    """`(tables emptied, rows deleted)`, in one transaction: all or nothing."""
    tables = tuple(
        table
        for table in reversed(all_user_tables())  # children before their parents
        if table.name != AccountVectorPurge.__tablename__
        and not (keep_user and table.name == "users")
    )
    rows = 0
    async with rt.session_factory() as db, db.begin():
        for table in tables:
            result = await db.execute(delete(table).where(table.c.user_id == user_id))
            rows += max(cast(CursorResult[Any], result).rowcount, 0)
        if not keep_user:
            await queue_vector_purge(db, user_id)
    return len(tables), rows


async def delete_account(
    rt: AccountRuntime, user_id: str, *, auth_mode: Literal["local", "google"]
) -> bool:
    """Erases everything `user_id` created. Local mode: the `users` row stays (the application
    goes on, empty); Google mode: it goes too, along with the login sessions.
    Returns false if only the final vector purge of a Google account is still pending."""
    started = time.monotonic()
    async with export_lock(rt.locks, user_id), rt.runtime.refusing_starts(user_id):
        cancelled = await _cancel_open_sessions(rt, user_id)
        await _delete_vectors(rt, user_id)
        files = await _delete_files(rt, user_id)
        cancelled += await _cancel_open_sessions(rt, user_id)  # just before reading the threads
        threads = await _session_ids(rt, user_id)
        await rt.runtime.delete_threads(threads)
        tables, rows = await _delete_rows(rt, user_id, keep_user=auth_mode == "local")
        complete = True
        if auth_mode == "google":
            complete = await finish_vector_purge(rt.session_factory, rt.indexer, user_id)
        else:
            await _delete_vectors(rt, user_id, rows_deleted=True)
    logger.info(
        "Delete everything: user=%s sessions_cancelled=%d threads=%d files=%d tables=%d rows=%d"
        " duration_ms=%d",
        user_id,
        cancelled,
        len(threads),
        files,
        tables,
        rows,
        round((time.monotonic() - started) * 1000),
    )
    return complete
