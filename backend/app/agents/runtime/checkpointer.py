"""Graph checkpointer: async SQLite in `checkpoints.db`, separated from the business database
(SPEC 9.4). The thread (`thread_id`) of a session is its identifier."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def open_checkpointer(path: Path) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    """Opens (and creates if needed, folder included) the file; a single `aiosqlite` connection
    shared by all sessions of the process, closed on exit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        await saver.setup()  # tables and WAL right away, not at the first graph
        yield saver


def thread_config(session_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": session_id}}
