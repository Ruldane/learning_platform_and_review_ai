"""L'état d'une ligne de table, en valeurs JSON (phase 10, P14) : ce que garde l'historique des
changements, et son inverse pour restaurer. Les tables à secret (colonne `info={"export": False}`),
`api_keys` et les tables `mcp_*` ne sont jamais recopiées (D200 n° 9)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Table

_NEVER_RECORDED = frozenset({"api_keys", "auth_sessions"})


@dataclass(frozen=True)
class UndoResult:
    """`undone` : le nombre de lignes remises dans leur état d'avant."""

    call_id: str
    undone: int


def recordable(table: Table) -> bool:
    """Une table dont l'historique est permis : clé primaire simple, aucun secret (ni colonne ni
    table marquée `info={"export": False}`), pas `mcp_*`."""
    if table.name in _NEVER_RECORDED or table.name.startswith("mcp_"):
        return False
    if table.info.get("export", True) is False:
        return False
    if len(table.primary_key.columns) != 1:
        return False
    return all(column.info.get("export", True) is not False for column in table.columns)


def volatile_columns(table: Table) -> frozenset[str]:
    """Les colonnes que l'annulation ne compare pas et remet à vide (`info={"undo_volatile":
    True}`) : posées hors de l'appel par un traitement de fond (l'indexation de la mémoire)."""
    return frozenset(c.name for c in table.columns if c.info.get("undo_volatile"))


def counter_columns(table: Table) -> frozenset[str]:
    """Les compteurs de version (`info={"undo_counter": True}`) : l'annulation d'une modification
    les **avance** au lieu de les ramener à leur ancienne valeur, pour qu'une lecture faite avant
    l'annulation reste périmée (jamais de retour à une valeur déjà vue)."""
    return frozenset(c.name for c in table.columns if c.info.get("undo_counter"))


def derived(table: Table) -> bool:
    """Table dont les lignes se déduisent de la ligne qu'elles visent (`info={"undo_derived":
    True}`) : retirer l'ajout les retire avec lui (clé étrangère en cascade), elles ne le
    « retiennent » pas."""
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
    """Les colonnes d'une ligne, en valeurs JSON (dates en texte ISO)."""
    return {column.name: jsonable(row[column.name]) for column in table.columns}


def revive(table: Table, values: dict[str, Any]) -> dict[str, Any]:
    """L'inverse de `snapshot` pour les dates et les décimaux (les autres valeurs sont telles
    quelles)."""
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
