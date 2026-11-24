"""Write both new files without changing the served edition's pointers."""

import asyncio
import logging
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass

from app.features.book.service.compiler import BookFiles
from app.providers.storage.base import FileStorage

logger = logging.getLogger(__name__)
_CATEGORY = "book"


@dataclass(frozen=True)
class BookKeys:
    pdf: str
    epub: str


async def _discard(storage: FileStorage, user_id: str, keys: Iterable[str]) -> None:
    for key in keys:
        try:
            await storage.delete(user_id, key)
        except Exception as error:
            logger.warning("Edition cleanup (%s)", type(error).__name__)


async def discard_book(storage: FileStorage, user_id: str, keys: BookKeys) -> None:
    """Remove files that were not kept, or those of an old, already replaced edition."""
    await _discard(storage, user_id, (keys.pdf, keys.epub))


async def _save(
    storage: FileStorage, user_id: str, data: bytes, suffix: str, staged: list[str]
) -> str:
    # A local write may continue in its thread after cancellation. Waiting for its key lets
    # us delete that file too, before handing the cancellation back to the caller.
    writing = asyncio.create_task(storage.save(user_id, _CATEGORY, data, suffix))
    try:
        key = await asyncio.shield(writing)
    except asyncio.CancelledError:
        with suppress(Exception):
            staged.append(await writing)
        raise
    staged.append(key)
    return key


async def stage_book(storage: FileStorage, user_id: str, files: BookFiles) -> BookKeys:
    """Prepare two account keys to publish together in the integration transaction."""
    staged: list[str] = []
    try:
        pdf = await _save(storage, user_id, files.pdf, ".pdf", staged)
        epub = await _save(storage, user_id, files.epub, ".epub", staged)
    except (Exception, asyncio.CancelledError):
        await _discard(storage, user_id, staged)
        raise
    return BookKeys(pdf=pdf, epub=epub)
