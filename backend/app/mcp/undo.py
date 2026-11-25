"""Undo of the changes of a level 2 call (phase 10, P14): in a transaction, **if each row is still
in the "after" state**, the additions are deleted, the changes restored and the deletions
re-inserted; otherwise 409 with nothing written. Only this user's rows are seen (404 for another
user's call).

Safeguards: (1) the call's rows are first claimed by an `UPDATE … WHERE undone_at IS NULL` (two
clicks at the same time: only one gets through); (2) an addition that has **linked** rows (foreign
key, cascade included) not coming from the same call is not deleted: the deletion would silently
take them with it (`undo_has_dependents`); (3) a database constraint is a 409, never a 500."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import Base
from app.db.models.agents import OPEN_SESSION_STATES, AgentSession
from app.db.models.mcp import McpChange
from app.mcp.rowstate import (
    UndoResult,
    counter_columns,
    derived,
    recordable,
    revive,
    snapshot,
    volatile_columns,
)


async def undo_call(
    factory: async_sessionmaker[AsyncSession], user_id: str, call_id: str
) -> UndoResult:
    """Undoes all the changes of `call_id`, or nothing: 404 if the call changed nothing for this
    user,
    409 if it is already undone, if a row has changed since, if an addition has linked rows from
    another call, or if the database refuses."""
    async with factory() as db:
        stmt = (
            select(McpChange)
            .where(McpChange.user_id == user_id, McpChange.call_id == call_id)
            .order_by(McpChange.created_at.desc(), McpChange.id.desc())
        )
        rows = list((await db.execute(stmt)).scalars())
        if not rows:
            raise AppError("call_not_found", "No change to undo for this call.", 404)
        pending = [row for row in rows if row.undone_at is None]
        if not pending:
            raise _already_undone()
        try:
            await _claim(db, user_id, call_id, pending)
            added = {(row.table_name, row.row_id) for row in pending if row.op == "insert"}
            for row in pending:
                if row.op == "insert":
                    await _check_dependents(db, row, added)
            for row in pending:
                await _check(db, row)
            cancelled = await _cancel_pending_sessions(db, user_id, pending)
            for row in pending:
                await _apply(db, row, user_id)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise AppError(
                "undo_refused",
                "Undo refused: the database refuses to revert this change (a constraint would "
                "be violated).",
                409,
            ) from exc
        except AppError:
            await db.rollback()  # the « pris » mark set by `_claim` does not stay
            raise
    return UndoResult(call_id=call_id, undone=len(pending), cancelled_sessions=cancelled)


async def _cancel_pending_sessions(
    db: AsyncSession, user_id: str, changes: list[McpChange]
) -> tuple[str, ...]:
    """Revokes, with the write, the session that this call had put on hold."""
    cancelled: list[str] = []
    for row in changes:
        for column in _table(row).columns:
            if not (
                column.info.get("undo_pending_session")
                or column.info.get("undo_publication_session")
            ):
                continue
            old = (row.before or {}).get(column.name)
            sid = (row.after or {}).get(column.name)
            if isinstance(sid, str) and sid != old and await _cancel_session(db, user_id, sid):
                cancelled.append(sid)
    return tuple(cancelled)


async def _cancel_session(db: AsyncSession, user_id: str, sid: str) -> bool:
    stmt = (
        update(AgentSession)
        .where(
            AgentSession.user_id == user_id,
            AgentSession.id == sid,
            AgentSession.status.in_(OPEN_SESSION_STATES),
        )
        .values(status="cancelled", pending_interrupt=None)
        .returning(AgentSession.id)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def _already_undone() -> AppError:
    return AppError("already_undone", "This call is already undone.", 409)


async def _claim(db: AsyncSession, user_id: str, call_id: str, pending: list[McpChange]) -> None:
    """Claims the history rows (`undone_at`) first: a second click, finding them claimed, gets 409
    without applying anything."""
    taken = await db.execute(
        update(McpChange)
        .where(
            McpChange.user_id == user_id,
            McpChange.call_id == call_id,
            McpChange.id.in_([row.id for row in pending]),
            McpChange.undone_at.is_(None),
        )
        .values(undone_at=datetime.now(UTC))
    )
    if int(getattr(taken, "rowcount", 0) or 0) != len(pending):
        raise _already_undone()


async def _check_dependents(db: AsyncSession, row: McpChange, added: set[tuple[str, str]]) -> None:
    """An addition is deleted only if no row is attached to it (foreign key, cascade or not) outside
    those this call added itself; otherwise 409, without content."""
    table = _table(row)
    for child, column, parent in _referrers(table):
        value = row.row_id if parent.primary_key else (row.after or {}).get(parent.name)
        keys = list(child.primary_key.columns)
        found = (await db.execute(select(*keys).where(column == value))).all()
        for dependent in found:
            same_call = recordable(child) and (child.name, str(dependent[0])) in added
            if not same_call and not derived(child):
                raise AppError(
                    "undo_has_dependents",
                    f"Undo refused: rows of '{child.name}' were added since and depend on this "
                    "addition; reverting it would delete them with it.",
                    409,
                    {"table": child.name},
                )


def _referrers(table: Table) -> list[tuple[Table, Column[Any], Column[Any]]]:
    """Columns of other tables (or of the same one) that point at this table through a foreign key:
    `(linked table, linked column, targeted column)`."""
    found: list[tuple[Table, Column[Any], Column[Any]]] = []
    for other in Base.metadata.tables.values():
        for key in other.foreign_keys:
            if key.column.table is table:
                found.append((other, key.parent, key.column))
    return found


def _table(row: McpChange) -> Table:
    table = Base.metadata.tables.get(row.table_name)
    if table is None or not recordable(table):
        raise AppError("undo_refused", "Undo refused: table cannot be undone.", 409)
    return table


async def _current(db: AsyncSession, row: McpChange) -> dict[str, Any] | None:
    table = _table(row)
    pk = next(iter(table.primary_key.columns))
    found = (await db.execute(select(table).where(pk == row.row_id))).mappings().first()
    return None if found is None else snapshot(table, found)


def _without(state: dict[str, Any] | None, ignored: frozenset[str]) -> dict[str, Any] | None:
    # A nullable column added after the call is NULL in its historical snapshot.
    return (
        None
        if state is None
        else {k: v for k, v in state.items() if k not in ignored and v is not None}
    )


def _pending_attachments(table: Table, row: McpChange) -> frozenset[str]:
    """A PDF of the text still published can arrive while the draft is being checked."""
    if any(
        c.info.get("undo_pending_session") and (row.after or {}).get(c.name) for c in table.columns
    ):
        return frozenset(c.name for c in table.columns if c.info.get("undo_pending_attachment"))
    return frozenset()


async def _check(db: AsyncSession, row: McpChange) -> None:
    """Is the row still as the call left it? Otherwise 409, without its content."""
    expected = None if row.op == "delete" else row.after
    table = _table(row)
    ignored = volatile_columns(table) | _pending_attachments(table, row)
    current = await _current(db, row)
    if _without(current, ignored) != _without(expected, ignored):
        raise AppError(
            "undo_refused",
            f"Undo refused: a row of '{row.table_name}' has changed since this call; "
            "reverting it would overwrite a more recent change.",
            409,
            {"table": row.table_name},
        )


async def _apply(db: AsyncSession, row: McpChange, user_id: str) -> None:
    table = _table(row)
    pk = next(iter(table.primary_key.columns))
    scope = [table.c.user_id == user_id] if "user_id" in table.c else []
    if row.op == "insert":
        await db.execute(delete(table).where(pk == row.row_id, *scope))
        return
    values = revive(table, dict(row.before or {}))
    values.update({name: None for name in volatile_columns(table) if name in values})
    if row.op == "update":
        values.pop(pk.name, None)
        for name in _pending_attachments(table, row):
            values.pop(name, None)
        values.update(
            {name: table.c[name] + 1 for name in counter_columns(table) if name in values}
        )
        await db.execute(update(table).where(pk == row.row_id, *scope).values(**values))
    else:
        await db.execute(insert(table).values(**values))
