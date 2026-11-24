import asyncio
from collections.abc import Coroutine
from typing import Any

from starlette.types import Receive

from app.core.errors import AppError


async def _wait_for_disconnect(receive: Receive) -> None:
    while (await receive())["type"] != "http.disconnect":
        pass


async def until_disconnect[T](receive: Receive, operation: Coroutine[Any, Any, T]) -> T:
    """Une opération distante n’a plus de destinataire une fois le navigateur parti."""
    work = asyncio.create_task(operation)
    closed = asyncio.create_task(_wait_for_disconnect(receive))
    try:
        await asyncio.wait((work, closed), return_when=asyncio.FIRST_COMPLETED)
        if work.done():
            return work.result()
        raise AppError("voice_cancelled", "Audio operation cancelled.", 499)
    finally:
        work.cancel()
        closed.cancel()
        await asyncio.gather(work, closed, return_exceptions=True)
