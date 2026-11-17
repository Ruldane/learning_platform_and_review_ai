"""Quelles tables partent dans l'export, avec quelles colonnes, et la forme JSON d'une ligne.

Les tables se lisent dans `Base.metadata` : toute table qui a une colonne `user_id` est exportée,
y compris celle qu'une feature ajoutera demain, sans rien changer ici."""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from sqlalchemy import Column, Table

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.db.base import Base

# Jamais exportées : les sessions de connexion ne portent que l'empreinte d'un jeton.
EXCLUDED_TABLES = frozenset({"auth_sessions"})
# Colonnes jamais lues ni écrites : la clé d'API chiffrée ne sort pas (seuls `last4` et l'état
# du dernier test restent).
REDACTED_COLUMNS: Mapping[str, frozenset[str]] = {"api_keys": frozenset({"encrypted_key"})}


def user_tables() -> list[Table]:
    """Les tables à exporter, dans l'ordre des dépendances : celles de `Base.metadata` qui ont
    une colonne `user_id`, sauf `EXCLUDED_TABLES`."""
    return [
        table
        for table in Base.metadata.sorted_tables
        if "user_id" in table.c and table.name not in EXCLUDED_TABLES
    ]


def exported_columns(table: Table) -> list[Column[Any]]:
    """Les colonnes de `table` qui sortent : toutes, sauf `REDACTED_COLUMNS`."""
    hidden = REDACTED_COLUMNS.get(table.name, frozenset())
    return [column for column in table.c if column.name not in hidden]


def row_json(row: Mapping[str, Any]) -> dict[str, Any]:
    """Une ligne prête pour `json.dumps` : dates et heures en ISO 8601, le reste tel quel (les
    colonnes JSON sont déjà des dictionnaires et des listes)."""
    return {
        name: value.isoformat() if isinstance(value, datetime | date) else value
        for name, value in row.items()
    }
