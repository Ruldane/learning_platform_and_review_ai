from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from app.features.memory.service.runtime import MemoryRuntime


def get_memory_runtime(conn: HTTPConnection) -> MemoryRuntime:
    """La mémoire ouverte par le lifespan (`app.state.memory`)."""
    runtime: MemoryRuntime = conn.app.state.memory
    return runtime


MemoryRuntimeDep = Annotated[MemoryRuntime, Depends(get_memory_runtime)]
