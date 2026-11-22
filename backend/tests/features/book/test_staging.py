import asyncio
from unittest.mock import AsyncMock, call

import pytest

from app.features.book.service.compiler import BookFiles
from app.features.book.service.staging import BookKeys, stage_book
from app.providers.storage.base import FileStorage

FILES = BookFiles(pdf=b"%PDF", epub=b"EPUB")
PDF_KEY = "owner/book/new.pdf"
EPUB_KEY = "owner/book/new.epub"


async def test_stage_persists_only_new_files_for_the_chosen_owner() -> None:
    storage = AsyncMock(spec=FileStorage)
    storage.save.side_effect = [PDF_KEY, EPUB_KEY]

    assert await stage_book(storage, "owner", FILES) == BookKeys(pdf=PDF_KEY, epub=EPUB_KEY)
    assert storage.save.await_args_list == [
        call("owner", "book", FILES.pdf, ".pdf"),
        call("owner", "book", FILES.epub, ".epub"),
    ]
    storage.delete.assert_not_awaited()


async def test_stage_deletes_the_unpublished_pdf_if_epub_write_fails() -> None:
    storage = AsyncMock(spec=FileStorage)
    storage.save.side_effect = [PDF_KEY, OSError("disque plein")]
    with pytest.raises(OSError):
        await stage_book(storage, "owner", FILES)
    storage.delete.assert_awaited_once_with("owner", PDF_KEY)


async def test_stage_cleans_files_when_cancelled_during_a_save() -> None:
    storage = AsyncMock(spec=FileStorage)
    started = asyncio.Event()
    release = asyncio.Event()

    async def save(user_id: str, category: str, data: bytes, suffix: str) -> str:
        if suffix == ".pdf":
            return PDF_KEY
        started.set()
        await release.wait()
        return EPUB_KEY

    storage.save.side_effect = save
    staging = asyncio.create_task(stage_book(storage, "owner", FILES))
    await asyncio.wait_for(started.wait(), timeout=1)
    staging.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await staging
    assert storage.delete.await_args_list == [call("owner", PDF_KEY), call("owner", EPUB_KEY)]
