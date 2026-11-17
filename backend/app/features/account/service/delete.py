"""« Tout supprimer » (P19) : l'ordre est celui qui se rejoue jusqu'au bout.

Sessions actives annulées, puis vecteurs, fichiers, points de reprise des sessions, enfin les
lignes de **toutes** les tables à `user_id` (`all_user_tables`) dans une seule transaction, enfants
d'abord. Chaque étape est idempotente et la base ne change qu'à la fin : un appel interrompu
(Qdrant en panne, disque verrouillé) se refait entier, et rien n'est supprimé en base tant que
les vecteurs, les fichiers et les points de reprise ne le sont pas.

Même verrou par compte que l'export : les deux ne se croisent pas. Les journaux ne portent que
l'identifiant, des nombres et la durée.
"""

import logging
import time
from typing import Any, Literal, cast

from sqlalchemy import delete
from sqlalchemy.engine import CursorResult

from app.agents.runtime.control import OPEN
from app.core.errors import AppError
from app.db.base import Base
from app.features.account.repository import AccountRepository
from app.features.account.service.export import export_lock
from app.features.account.service.runtime import AccountRuntime
from app.features.account.service.tables import all_user_tables
from app.providers.vector.base import VectorStoreUnavailable

logger = logging.getLogger(__name__)

NOT_CANCELLABLE = "session_not_cancellable"  # terminée entre la lecture et l'annulation
_SESSIONS = Base.metadata.tables["sessions"]


async def _sessions(rt: AccountRuntime, user_id: str) -> list[dict[str, Any]]:
    async with rt.session_factory() as db:
        return await AccountRepository(db, user_id).rows(
            _SESSIONS, [_SESSIONS.c.id, _SESSIONS.c.status]
        )


async def _cancel_open_sessions(rt: AccountRuntime, user_id: str) -> int:
    """Annule les sessions `running`, `waiting_user` et `paused` : plus aucune tâche n'écrit dans
    la base ni dans les points de reprise du compte. Une session qui vient de finir est laissée."""
    cancelled = 0
    for row in await _sessions(rt, user_id):
        if row["status"] not in OPEN:
            continue
        try:
            await rt.runtime.runner.cancel(user_id, row["id"])
            cancelled += 1
        except AppError as exc:
            if exc.code != NOT_CANCELLABLE:
                raise
    return cancelled


async def _delete_vectors(rt: AccountRuntime, user_id: str) -> None:
    try:
        await rt.index.delete_user(user_id)
    except VectorStoreUnavailable:
        raise AppError(
            "vector_store_unavailable",
            "La base vectorielle est indisponible : rien n'est supprimé en base, réessaie.",
            503,
        ) from None


async def _delete_rows(rt: AccountRuntime, user_id: str, *, keep_user: bool) -> tuple[int, int]:
    """`(tables vidées, lignes supprimées)`, en une transaction : tout part ou rien."""
    tables = tuple(
        table
        for table in reversed(all_user_tables())  # les enfants avant leurs parents
        if not (keep_user and table.name == "users")
    )
    rows = 0
    async with rt.session_factory() as db, db.begin():
        for table in tables:
            result = await db.execute(delete(table).where(table.c.user_id == user_id))
            rows += max(cast(CursorResult[Any], result).rowcount, 0)
    return len(tables), rows


async def delete_account(
    rt: AccountRuntime, user_id: str, *, auth_mode: Literal["local", "google"]
) -> None:
    """Efface tout ce que `user_id` a posé. Mode local : la ligne `users` reste (l'application
    continue, vide) ; mode Google : elle part aussi, avec les sessions de connexion."""
    started = time.monotonic()
    async with export_lock(rt.locks, user_id):
        cancelled = await _cancel_open_sessions(rt, user_id)
        await _delete_vectors(rt, user_id)
        files = await rt.storage.delete_user(user_id)
        threads = [row["id"] for row in await _sessions(rt, user_id)]
        await rt.runtime.delete_threads(threads)
        tables, rows = await _delete_rows(rt, user_id, keep_user=auth_mode == "local")
    logger.info(
        "Tout supprimer : user=%s sessions_cancelled=%d threads=%d files=%d tables=%d rows=%d"
        " duration_ms=%d",
        user_id,
        cancelled,
        len(threads),
        files,
        tables,
        rows,
        round((time.monotonic() - started) * 1000),
    )
