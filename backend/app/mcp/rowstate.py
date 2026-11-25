"""The state of a table row, in JSON values (phase 10, P14): what the change history keeps, and its
inverse to restore. Tables with a secret (column `info={"export": False}`), `api_keys` and the
`mcp_*` tables are never copied (D200 no. 9)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Table

_NEVER_RECORDED = frozenset({"api_keys", "auth_sessions"})


@dataclass(frozen=True)
class UndoResult:
    """`undone`: the number of rows put back in their earlier state."""

    call_id: str
    undone: int
    cancelled_sessions: tuple[str, ...] = ()


def recordable(table: Table) -> bool:
    """A table whose history is allowed: simple primary key, no secret (neither a column nor a table
    marked `info={"export": False}`), not `mcp_*`."""
    if table.name in _NEVER_RECORDED or table.name.startswith("mcp_"):
        return False
    if table.info.get("export", True) is False:
        return False
    if len(table.primary_key.columns) != 1:
        return False
    return all(column.info.get("export", True) is not False for column in table.columns)


def volatile_columns(table: Table) -> frozenset[str]:
    """The columns that undo does not compare and resets to empty (`info={"undo_volatile": True}`):
    set outside the call by a background process (the memory indexing)."""
    return frozenset(c.name for c in table.columns if c.info.get("undo_volatile"))


def counter_columns(table: Table) -> frozenset[str]:
    """The version counters (`info={"undo_counter": True}`): undoing a change **advances** them
    instead
    of putting them back to their old value, so that a read made before the undo stays stale
    (never a return to a value already seen)."""
    return frozenset(c.name for c in table.columns if c.info.get("undo_counter"))


def derived(table: Table) -> bool:
    """A table whose rows derive from the row they target (`info={"undo_derived": True}`): removing
    the
    addition removes them with it (cascading foreign key); they do not keep it alive."""
    return bool(table.info.get("undo_derived"))


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str | dict | list):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def snapshot(table: Table, row: Any) -> dict[str, Any]:
    """The columns of a row, in JSON values (dates as ISO text)."""
    return {column.name: jsonable(row[column.name]) for column in table.columns}


def revive(table: Table, values: dict[str, Any]) -> dict[str, Any]:
    """The inverse of `snapshot` for dates and decimals (other values are kept as they are)."""
    out: dict[str, Any] = {}
    for name, value in values.items():
        column_type = table.c[name].type
        try:
            kind = getattr(column_type, "impl_instance", column_type).python_type
        except NotImplementedError:
            kind = object
        if isinstance(value, str) and kind is datetime:
            value = datetime.fromisoformat(value)
        elif isinstance(value, str) and kind is date:
            value = date.fromisoformat(value)
        elif isinstance(value, str) and kind is Decimal:
            value = Decimal(value)
        out[name] = value
    return out
