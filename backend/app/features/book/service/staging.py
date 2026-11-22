"""Écrit les deux nouveaux fichiers sans modifier les pointeurs de l'édition servie."""

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
            logger.warning("Nettoyage d'une édition (%s)", type(error).__name__)


async def discard_book(storage: FileStorage, user_id: str, keys: BookKeys) -> None:
    """Retire les fichiers non retenus, ou ceux d'une ancienne édition déjà remplacée."""
    await _discard(storage, user_id, (keys.pdf, keys.epub))


async def _save(
    storage: FileStorage, user_id: str, data: bytes, suffix: str, staged: list[str]
) -> str:
    # Une écriture locale peut continuer dans son thread après l'annulation. Attendre sa
    # clé permet de supprimer aussi ce fichier, avant de rendre l'annulation à l'appelant.
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
    """Prépare deux clés du compte à publier ensemble dans la transaction d'intégration."""
    staged: list[str] = []
    try:
        pdf = await _save(storage, user_id, files.pdf, ".pdf", staged)
        epub = await _save(storage, user_id, files.epub, ".epub", staged)
    except (Exception, asyncio.CancelledError):
        await _discard(storage, user_id, staged)
        raise
    return BookKeys(pdf=pdf, epub=epub)
