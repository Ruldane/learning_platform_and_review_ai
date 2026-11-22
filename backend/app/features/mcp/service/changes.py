"""L'historique des changements de Claude (niveau 2) tel que le voit January : un appel par ligne,
annulable d'un geste (`ChangeRecorder.undo`, dans `app/mcp/recorder.py`). Annuler remet les lignes
de l'appel dans leur état d'avant, ou refuse (409) si l'une d'elles a changé depuis."""

from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.mcp import McpChange
from app.features.mcp.repository import ChangeRepository
from app.features.mcp.schemas import McpChangeOut
from app.features.mcp.service.calls import RETENTION_DAYS
from app.mcp.recorder import ChangeRecorder
from app.mcp.rowstate import UndoResult


async def purge_old_changes(
    session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> int:
    """Retire les changements de plus de `RETENTION_DAYS` jours (ils gardent l'avant et l'après de
    chaque ligne, texte complet ; passé ce délai l'appel ne s'annule plus). Tâche planifiée, tous
    comptes : une rétention. Rend le nombre de lignes retirées."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    async with session_factory() as db:
        result = await db.execute(delete(McpChange).where(McpChange.created_at < cutoff))
        await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)


class ChangesService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], user_id: str) -> None:
        self._factory = session_factory
        self._user_id = user_id

    async def recent(self, limit: int) -> list[McpChangeOut]:
        async with self._factory() as db:
            repo = ChangeRepository(db, self._user_id)
            calls = await repo.calls(limit)
            ids = [call_id for call_id, *_ in calls]
            tables = await repo.tables(ids)
            actions = await repo.actions(ids)
        return [
            _out(call_id, count, when, undone, tables.get(call_id, []), actions.get(call_id))
            for call_id, count, when, undone in calls
        ]

    async def undo(self, call_id: str) -> UndoResult:
        recorder = ChangeRecorder(self._factory, call_id, self._user_id)
        return await recorder.undo(call_id)


def _out(
    call_id: str,
    count: int,
    when: datetime,
    undone: datetime | None,
    tables: list[str],
    action: str | None,
) -> McpChangeOut:
    return McpChangeOut(
        call_id=call_id,
        action=action or "?",
        rows=count,
        tables=tables,
        undone_at=undone,
        created_at=when,
    )
