"""L'annulation des changements d'un appel de niveau 2 (phase 10, P14) : dans une transaction, **si
chaque ligne est restée dans l'état « après »**, les ajouts sont supprimés, les modifications
restaurées et les suppressions ré-insérées ; sinon 409 sans rien écrire. Seules les lignes de
cette utilisatrice sont vues (404 pour l'appel d'une autre)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Table, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import Base
from app.db.models.mcp import McpChange
from app.mcp.rowstate import UndoResult, recordable, revive, snapshot


async def undo_call(
    factory: async_sessionmaker[AsyncSession], user_id: str, call_id: str
) -> UndoResult:
    """Annule tous les changements de `call_id` ou rien : 404 si l'appel n'a rien changé chez
    cette utilisatrice, 409 s'il est déjà annulé ou si une ligne a changé depuis."""
    async with factory() as db:
        stmt = (
            select(McpChange)
            .where(McpChange.user_id == user_id, McpChange.call_id == call_id)
            .order_by(McpChange.created_at.desc(), McpChange.id.desc())
        )
        rows = list((await db.execute(stmt)).scalars())
        if not rows:
            raise AppError("call_not_found", "Aucun changement à annuler pour cet appel.", 404)
        pending = [row for row in rows if row.undone_at is None]
        if not pending:
            raise AppError("already_undone", "Cet appel est déjà annulé.", 409)
        for row in pending:
            await _check(db, row)
        now = datetime.now(UTC)
        for row in pending:
            await _apply(db, row, user_id)
            row.undone_at = now
        await db.commit()
    return UndoResult(call_id=call_id, undone=len(pending))


def _table(row: McpChange) -> Table:
    table = Base.metadata.tables.get(row.table_name)
    if table is None or not recordable(table):
        raise AppError("undo_refused", "Annulation refusée : table non annulable.", 409)
    return table


async def _current(db: AsyncSession, row: McpChange) -> dict[str, Any] | None:
    table = _table(row)
    pk = next(iter(table.primary_key.columns))
    found = (await db.execute(select(table).where(pk == row.row_id))).mappings().first()
    return None if found is None else snapshot(table, found)


async def _check(db: AsyncSession, row: McpChange) -> None:
    """La ligne est-elle restée comme l'appel l'a laissée ? Sinon 409, sans son contenu."""
    expected = None if row.op == "delete" else row.after
    if await _current(db, row) != expected:
        raise AppError(
            "undo_refused",
            f"Annulation refusée : une ligne de « {row.table_name} » a changé depuis cet "
            "appel ; la défaire écraserait un changement plus récent.",
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
    if row.op == "update":
        values.pop(pk.name, None)
        await db.execute(update(table).where(pk == row.row_id, *scope).values(**values))
    else:
        await db.execute(insert(table).values(**values))
