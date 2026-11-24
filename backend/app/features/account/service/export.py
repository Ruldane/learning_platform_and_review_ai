"""Export of all of a user's data (P18): a zip archive written to a temporary file (in memory
up to 32 MB, then on disk), then served in 64 KiB chunks. The one-export-per-account lock is
taken by the caller (`export_lock`).

Contents: `manifest.json`, `tables/<table>.json` for each table that has `user_id` (except those
their model excludes; `api_keys` without the encrypted key), `files/<key>` for each uploaded file
(the storage key, `<user_id>/` prefix included, as in the tables). Neither vectors nor agent
checkpoints: they can be recomputed. Tables are read in batches (`BATCH_ROWS`) and streamed into
the zip entry. Logs only carry ids, numbers and the duration."""

import asyncio
import json
import logging
import os
import tempfile
import time
import zipfile
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.features.account.repository import AccountRepository
from app.features.account.service.tables import (
    exported_columns,
    json_default,
    row_json,
    user_tables,
)
from app.features.postings.service.runtime import KeyLocks
from app.features.settings.service import SettingsService
from app.providers.storage.base import FileStorage

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1
CHUNK_BYTES = 64 * 1024
SPOOL_MAX_BYTES = 32 * 1024 * 1024
BATCH_ROWS = 500  # rows read then written at a time: a table's memory does not depend on its size


def export_filename(now: datetime, zone: ZoneInfo) -> str:
    """`tremplin-export-YYYYMMDD.zip`, the day being the user's local day."""
    return f"tremplin-export-{now.astimezone(zone):%Y%m%d}.zip"


def export_lock(locks: KeyLocks, user_id: str) -> asyncio.Lock:
    """One export at a time per account: a second call waits for the first to finish."""
    return locks.get(user_id, "export")


async def user_export_zone(db: AsyncSession, user_id: str) -> ZoneInfo:
    """The time zone from the user's settings (`Europe/Paris` if unknown)."""
    return user_zone((await SettingsService(db, user_id).get()).timezone)


def _entry(name: str, now: datetime) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=now.astimezone(UTC).timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    return info


def _encode(rows: list[dict[str, Any]], *, first: bool) -> bytes:
    """A batch of rows: one JSON line per table row, separated by commas."""
    lines = [json.dumps(row_json(row), ensure_ascii=False, default=json_default) for row in rows]
    sep = "\n" if first else ",\n"
    return (sep + ",\n".join(lines)).encode()


async def _write_table(
    zf: zipfile.ZipFile,
    name: str,
    batches: AsyncGenerator[list[dict[str, Any]], None],
    now: datetime,
) -> int:
    """`tables/<name>.json`: a JSON array **streamed** batch by batch into the zip entry (a
    single open entry, one batch in memory); returns the number of rows written."""
    out = zf.open(_entry(f"tables/{name}.json", now), "w")
    count = 0
    try:
        async with aclosing(batches):  # also closed if writing fails (the session is released)
            await asyncio.to_thread(out.write, b"[")
            async for batch in batches:
                await asyncio.to_thread(out.write, _encode(batch, first=count == 0))
                count += len(batch)
            await asyncio.to_thread(out.write, b"\n]\n")
    finally:
        await asyncio.to_thread(out.close)
    return count


def _write_bytes(zf: zipfile.ZipFile, name: str, data: bytes, now: datetime) -> None:
    zf.writestr(_entry(name, now), data)


async def _write_files(
    zf: zipfile.ZipFile, storage: FileStorage, user_id: str, now: datetime
) -> int:
    """The uploaded files; a file deleted between the listing and the read is skipped."""
    written = 0
    for key in await storage.list_user(user_id):
        try:
            data = await storage.read(user_id, key)
        except FileNotFoundError:
            continue
        await asyncio.to_thread(_write_bytes, zf, f"files/{key}", data, now)
        written += 1
    return written


async def build_export(
    db: AsyncSession, storage: FileStorage, user_id: str, now: datetime
) -> tempfile.SpooledTemporaryFile[bytes]:
    """The archive of `user_id`, ready to read from the start. To be closed by the caller (the
    `stream_export` stream does it)."""
    started = time.monotonic()
    # Closed by `stream_export`, or here if building fails.
    spool: tempfile.SpooledTemporaryFile[bytes] = tempfile.SpooledTemporaryFile(  # noqa: SIM115
        max_size=SPOOL_MAX_BYTES
    )
    try:
        repository = AccountRepository(db, user_id)
        counts: dict[str, int] = {}
        with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED) as zf:
            for table in user_tables():
                batches = repository.batches(table, exported_columns(table), BATCH_ROWS)
                counts[table.name] = await _write_table(zf, table.name, batches, now)
            files = await _write_files(zf, storage, user_id, now)
            manifest = {
                "format_version": FORMAT_VERSION,
                "exported_at": now.astimezone(UTC).isoformat(),
                "user_id": user_id,
                "tables": counts,
                "files": files,
            }
            text = json.dumps(manifest, ensure_ascii=False, indent=2)
            await asyncio.to_thread(_write_bytes, zf, "manifest.json", text.encode(), now)
        spool.seek(0)
    except BaseException:
        spool.close()
        raise
    logger.info(
        "Data export: user=%s tables=%d rows=%d files=%d duration_ms=%d",
        user_id,
        len(counts),
        sum(counts.values()),
        files,
        int((time.monotonic() - started) * 1000),
    )
    return spool


def archive_size(spool: tempfile.SpooledTemporaryFile[bytes]) -> int:
    """The archive size; reading restarts from the beginning."""
    size = spool.seek(0, os.SEEK_END)
    spool.seek(0)
    return size


async def stream_export(spool: tempfile.SpooledTemporaryFile[bytes]) -> AsyncIterator[bytes]:
    """The archive in 64 KiB chunks; the file is closed at the end or if the client leaves."""
    try:
        while chunk := await asyncio.to_thread(spool.read, CHUNK_BYTES):
            yield chunk
    finally:
        spool.close()
