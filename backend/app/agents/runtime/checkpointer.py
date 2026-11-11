"""Checkpointer des graphes : SQLite asynchrone dans `checkpoints.db`, séparé de la base métier
(SPEC 9.4). Le fil (`thread_id`) d'une session est son identifiant."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def open_checkpointer(path: Path) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    """Ouvre (et crée au besoin, dossier compris) le fichier ; une seule connexion `aiosqlite`
    partagée par toutes les sessions du processus, fermée à la sortie."""
    path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        await saver.setup()  # tables et WAL tout de suite, pas au premier graphe
        yield saver


def thread_config(session_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": session_id}}
