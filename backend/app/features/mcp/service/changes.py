"""L'historique des changements de Claude (niveau 2) tel que le voit January : un appel par ligne,
annulable d'un geste (`ChangeRecorder.undo`, dans `app/mcp/recorder.py`). Annuler remet les lignes
de l'appel dans leur état d'avant, ou refuse (409) si l'une d'elles a changé depuis."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.mcp.repository import ChangeRepository
from app.features.mcp.schemas import McpChangeOut, McpUndoOut
from app.mcp.recorder import ChangeRecorder


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

    async def undo(self, call_id: str) -> McpUndoOut:
        recorder = ChangeRecorder(self._factory, call_id, self._user_id)
        result = await recorder.undo(call_id)
        return McpUndoOut(call_id=result.call_id, undone=result.undone)


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
