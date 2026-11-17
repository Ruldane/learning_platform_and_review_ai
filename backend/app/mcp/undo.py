"""L'annulation des changements d'un appel de niveau 2 (phase 10, P14) : dans une transaction, **si
chaque ligne est restée dans l'état « après »**, les ajouts sont supprimés, les modifications
restaurées et les suppressions ré-insérées ; sinon 409 sans rien écrire. Seules les lignes de
cette utilisatrice sont vues (404 pour l'appel d'une autre).

Garde-fous : (1) les lignes de l'appel sont prises d'abord par un `UPDATE … WHERE undone_at IS
NULL` (deux clics en même temps : un seul passe) ; (2) un ajout qui a des lignes **liées** (clé
étrangère, cascade comprise) ne venant pas du même appel n'est pas supprimé : la suppression les
emporterait en silence (`undo_has_dependents`) ; (3) une contrainte de la base est un 409, jamais
une 500."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import Base
from app.db.models.mcp import McpChange
from app.mcp.rowstate import UndoResult, derived, recordable, revive, snapshot, volatile_columns


async def undo_call(
    factory: async_sessionmaker[AsyncSession], user_id: str, call_id: str
) -> UndoResult:
    """Annule tous les changements de `call_id` ou rien : 404 si l'appel n'a rien changé chez
    cette utilisatrice, 409 s'il est déjà annulé, si une ligne a changé depuis, si un ajout a des
    lignes liées d'un autre appel, ou si la base refuse."""
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
            raise _already_undone()
        try:
            await _claim(db, user_id, call_id, pending)
            added = {(row.table_name, row.row_id) for row in pending if row.op == "insert"}
            for row in pending:
                if row.op == "insert":
                    await _check_dependents(db, row, added)
            for row in pending:
                await _check(db, row)
            for row in pending:
                await _apply(db, row, user_id)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise AppError(
                "undo_refused",
                "Annulation refusée : la base refuse de défaire ce changement (une contrainte "
                "serait violée).",
                409,
            ) from exc
        except AppError:
            await db.rollback()  # le « pris » de `_claim` ne reste pas
            raise
    return UndoResult(call_id=call_id, undone=len(pending))


def _already_undone() -> AppError:
    return AppError("already_undone", "Cet appel est déjà annulé.", 409)


async def _claim(db: AsyncSession, user_id: str, call_id: str, pending: list[McpChange]) -> None:
    """Prend les lignes de l'historique (`undone_at`) avant tout : un second clic, qui les trouve
    prises, reçoit 409 sans rien appliquer."""
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
    """Un ajout n'est supprimé que si aucune ligne ne s'y rattache (clé étrangère, cascade ou non)
    en dehors de celles que cet appel a ajoutées lui-même : sinon 409, sans contenu."""
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
                    f"Annulation refusée : des lignes de « {child.name} » ont été ajoutées "
                    "depuis et dépendent de cet ajout ; le défaire les supprimerait avec lui.",
                    409,
                    {"table": child.name},
                )


def _referrers(table: Table) -> list[tuple[Table, Column[Any], Column[Any]]]:
    """Les colonnes d'autres tables (ou de la même) qui visent cette table par une clé étrangère :
    `(table liée, colonne liée, colonne visée)`."""
    found: list[tuple[Table, Column[Any], Column[Any]]] = []
    for other in Base.metadata.tables.values():
        for key in other.foreign_keys:
            if key.column.table is table:
                found.append((other, key.parent, key.column))
    return found


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


def _without(state: dict[str, Any] | None, ignored: frozenset[str]) -> dict[str, Any] | None:
    return None if state is None else {k: v for k, v in state.items() if k not in ignored}


async def _check(db: AsyncSession, row: McpChange) -> None:
    """La ligne est-elle restée comme l'appel l'a laissée ? Sinon 409, sans son contenu."""
    expected = None if row.op == "delete" else row.after
    ignored = volatile_columns(_table(row))
    current = await _current(db, row)
    if _without(current, ignored) != _without(expected, ignored):
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
    values.update({name: None for name in volatile_columns(table) if name in values})
    if row.op == "update":
        values.pop(pk.name, None)
        await db.execute(update(table).where(pk == row.row_id, *scope).values(**values))
    else:
        await db.execute(insert(table).values(**values))
