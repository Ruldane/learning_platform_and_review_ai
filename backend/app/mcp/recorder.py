"""The change history of a level 2 call and its undo (phase 10, P14).

`ChangeRecorder` listens to SQLAlchemy's flush events (`before_flush`, `after_flush`), but
**only during the call** that activated it (context variable `ACTIVE`, never shared between
requests): for each row added, modified or deleted, it reads the state before and the state
after in the database. Rows are written to `mcp_changes` (`persist`) only once the request
succeeds, with the call identifier. `undo` puts a call's rows back to their earlier state, in a
transaction, **if each one is still in the "after" state**; otherwise 409, nothing is done.

Stated limits: only the database is covered (P14); a bulk write outside the ORM (direct
`update(...)` or `delete(...)`) is not seen; tables that hold a secret (column
`info={"export": False}`), `api_keys` and the `mcp_*` tables are never copied into the history
(D200 no. 9); beyond `MAX_ROWS` rows, the call is not undoable (nothing is kept, rather than a
partial undo)."""

import logging
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Any

from sqlalchemy import Connection, Table, event, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.db.models.mcp import McpChange
from app.mcp.rowstate import UndoResult, recordable, snapshot
from app.mcp.undo import undo_call

logger = logging.getLogger(__name__)

MAX_ROWS = 500
ACTIVE: ContextVar["ChangeRecorder | None"] = ContextVar("mcp_change_recorder", default=None)


@dataclass
class _Op:
    kind: str  # insert | update | delete
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class ChangeRecorder:
    """See the module. Use as `async with recorder:` around the internal request."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], call_id: str, user_id: str
    ) -> None:
        self._factory = session_factory
        self.call_id = call_id
        self.user_id = user_id
        self.active = False
        self.overflow = False
        self._ops: dict[tuple[str, str], _Op] = {}
        self._touched: dict[tuple[str, str], tuple[Table, str, dict[str, Any]]] = {}
        self._token: Token[ChangeRecorder | None] | None = None
        self._recorded: int | None = None

    async def __aenter__(self) -> "ChangeRecorder":
        self.active = True
        self._token = ACTIVE.set(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.active = False  # a background task that inherited the context records nothing anymore
        if self._token is not None:
            ACTIVE.reset(self._token)

    # --- flush events (sync, during the flush) -------------------------------------------

    @staticmethod
    def _row(connection: Connection, table: Table, row_id: Any) -> dict[str, Any] | None:
        pk = next(iter(table.primary_key.columns))
        found = connection.execute(select(table).where(pk == row_id)).mappings().first()
        return None if found is None else snapshot(table, found)

    @staticmethod
    def _target(obj: Any) -> tuple[Table, str] | None:
        mapper = inspect(obj).mapper
        table = mapper.local_table
        if not isinstance(table, Table) or not recordable(table):
            return None
        row_id = mapper.primary_key_from_instance(obj)[0]
        return None if row_id is None else (table, str(row_id))

    def before_flush(self, session: Session) -> None:
        connection = session.connection()
        changing = [(obj, "update") for obj in session.dirty if session.is_modified(obj)]
        changing += [(obj, "delete") for obj in session.deleted]
        for obj, kind in changing:
            target = self._target(obj)
            if target is None:
                continue
            table, row_id = target
            key = (table.name, row_id)
            if key in self._touched:
                continue
            before = (
                self._ops[key].after if key in self._ops else self._row(connection, table, row_id)
            )
            if before is not None:
                self._touched[key] = (table, kind, before)

    def after_flush(self, session: Session) -> None:
        connection = session.connection()
        for obj in session.new:
            target = self._target(obj)
            if target is not None:
                table, row_id = target
                after = self._row(connection, table, row_id)
                self._note((table.name, row_id), "insert", None, after)
        for key, (table, kind, before) in self._touched.items():
            after = None if kind == "delete" else self._row(connection, table, key[1])
            self._note(key, kind, before, after)
        self._touched.clear()
        if len(self._ops) > MAX_ROWS:
            self.overflow = True

    def _note(
        self, key: tuple[str, str], kind: str, before: dict[str, Any] | None, after: Any
    ) -> None:
        """Merges successive passes over the same row: added then modified = added, added then
        deleted =
        nothing, modified then deleted = deleted."""
        current = self._ops.get(key)
        if current is None:
            self._ops[key] = _Op(kind, before, after)
        elif current.kind == "insert":
            if kind == "delete":
                del self._ops[key]
            else:
                current.after = after
        elif kind == "delete":
            current.kind, current.after = "delete", None
        else:
            current.after = after

    # --- write and undo ----------------------------------------------------------------------

    async def persist(self) -> int:
        """Writes the call's history (in its own short session); returns the number of rows kept."""
        if self._recorded is not None:
            return self._recorded
        async with self._factory() as db:
            done = self._insert(db, self._kept())
            if done:
                await db.commit()
        return done

    def _kept(self) -> list[tuple[tuple[str, str], _Op]]:
        return [
            (key, op)
            for key, op in self._ops.items()
            if not (op.kind == "update" and op.before == op.after)
        ]

    def _insert(self, db: AsyncSession, kept: list[tuple[tuple[str, str], _Op]]) -> int:
        if self.overflow:
            logger.warning("MCP : appel %s non annulable (trop de lignes)", self.call_id)
            return 0
        base = datetime.now(UTC)
        for index, ((table, row_id), op) in enumerate(kept):
            db.add(
                McpChange(
                    user_id=self.user_id,
                    call_id=self.call_id,
                    table_name=table,
                    row_id=row_id,
                    op=op.kind,
                    before=op.before,
                    after=op.after,
                    created_at=base + timedelta(microseconds=index),
                )
            )
        return len(kept)

    async def persist_in(self, db: AsyncSession) -> None:
        """Keeps a reservation and its history in the same transaction."""
        await db.flush()
        self._recorded = self._insert(db, self._kept())

    async def extend_in(self, db: AsyncSession, *, keep_latest: frozenset[str]) -> None:
        """Merges the publication with the original call in the business transaction."""
        await db.flush()
        stmt = select(McpChange).where(
            McpChange.user_id == self.user_id,
            McpChange.call_id == self.call_id,
            McpChange.undone_at.is_(None),
        )
        existing = {(row.table_name, row.row_id): row for row in await db.scalars(stmt)}
        if not existing:  # expired history
            return
        kept = self._kept()
        if self.overflow or len(existing.keys() | {key for key, _ in kept}) > MAX_ROWS:
            return  # the old snapshot will make a partial undo be refused
        added = []
        for key, op in kept:
            previous = existing.get(key)
            if previous is None:
                added.append((key, op))
            else:
                if previous.before is not None and op.before is not None:
                    latest = {name: op.before[name] for name in keep_latest if name in op.before}
                    previous.before = previous.before | latest
                previous.after = op.after
        self._insert(db, added)

    async def undo(self, call_id: str) -> UndoResult:
        """Undoes the changes of `call_id` (see `app/mcp/undo.py`)."""
        return await undo_call(self._factory, self.user_id, call_id)


def _on_before_flush(session: Session, flush_context: Any, instances: Any) -> None:
    recorder = ACTIVE.get()
    if recorder is not None and recorder.active:
        recorder.before_flush(session)


def _on_after_flush(session: Session, flush_context: Any) -> None:
    recorder = ACTIVE.get()
    if recorder is not None and recorder.active:
        recorder.after_flush(session)


def install_recorder_events() -> None:
    """Installs the flush listeners (only once; no effect outside a recorded call)."""
    if not event.contains(Session, "before_flush", _on_before_flush):
        event.listen(Session, "before_flush", _on_before_flush)
        event.listen(Session, "after_flush", _on_after_flush)
