"""Reconstruit les éditions demandées sans transaction pendant le rendu."""

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass

from app.db.models.book import ProgramBook
from app.features.book.repository import BookRepository
from app.features.book.service.compiler import compile_book
from app.features.book.service.models import BookSource
from app.features.book.service.runtime import BookRuntime
from app.features.book.service.source import book_source, source_hash
from app.features.book.service.staging import BookKeys, discard_book, stage_book
from app.features.settings.service import scheduled_users

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Build:
    revision: int
    previous: BookKeys | None
    source: BookSource
    digest: str


def _previous(row: ProgramBook) -> BookKeys | None:
    if row.pdf_key is None or row.epub_key is None:
        return None
    return BookKeys(row.pdf_key, row.epub_key)


async def _settle(runtime: BookRuntime, user_id: str, build: _Build, files: BookKeys) -> None:
    kept = False
    try:
        async with runtime.session_factory() as db:
            current = await book_source(db, user_id, build.source.program_id)
            if source_hash(current) == build.digest:
                kept = await BookRepository(db, user_id).publish(
                    build.source.program_id,
                    build.revision,
                    build.digest,
                    (files.pdf, files.epub),
                    len(build.source.chapters),
                )
                try:
                    await db.commit()
                except Exception:
                    kept = False
                    raise
    finally:
        if not kept:
            await discard_book(runtime.storage, user_id, files)
    if kept and build.previous is not None:
        await discard_book(runtime.storage, user_id, build.previous)


async def _compile(runtime: BookRuntime, user_id: str, build: _Build) -> None:
    compiled = await compile_book(build.source, runtime.renderer)
    files = await stage_book(runtime.storage, user_id, compiled)
    committing = asyncio.create_task(_settle(runtime, user_id, build, files))
    try:
        await asyncio.shield(committing)
    except asyncio.CancelledError:
        # La publication et le nettoyage doivent observer le même résultat du commit.
        with suppress(Exception):
            await committing
        raise


async def refresh_book(runtime: BookRuntime, user_id: str, program_id: str) -> None:
    """Reprend une demande persistée, ou publie les nouveaux chapitres d'une édition."""
    async with runtime.session_factory() as db:
        row = await BookRepository(db, user_id).get(program_id)
        if row is None:
            return
        revision = row.revision
        previous = _previous(row)
        snapshot = await book_source(db, user_id, program_id)
        digest = source_hash(snapshot)
        if row.source_hash == digest and previous is not None:
            return
    try:
        await _compile(runtime, user_id, _Build(revision, previous, snapshot, digest))
    except Exception as error:
        logger.warning("Édition du programme %s en échec (%s)", program_id, type(error).__name__)
        async with runtime.session_factory() as db:
            await BookRepository(db, user_id).fail(program_id, revision)
            await db.commit()


async def refresh_books(runtime: BookRuntime) -> None:
    async with runtime.session_factory() as db:
        users = await scheduled_users(db)
    for user_id in users:
        async with runtime.session_factory() as db:
            requested = await BookRepository(db, user_id).program_ids()
        for program_id in requested:
            try:
                await refresh_book(runtime, user_id, program_id)
            except Exception as error:
                logger.warning(
                    "Lecture du livre %s en échec (%s)", program_id, type(error).__name__
                )
