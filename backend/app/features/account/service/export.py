"""L'export de toutes les données d'une utilisatrice (P18) : une archive zip écrite dans un
fichier temporaire (en mémoire jusqu'à 32 Mo, puis sur disque), servie ensuite par morceaux de
64 Kio. Le verrou d'un export par compte est pris par l'appelant (`export_lock`).

Contenu : `manifest.json`, `tables/<table>.json` pour chaque table qui a `user_id` (hors celles que
leur modèle écarte ; `api_keys` sans clé chiffrée), `files/<clé>` pour chaque fichier déposé (la
clé du stockage, préfixe `<user_id>/` compris, comme dans les tables). Ni vecteurs ni points de
reprise des agents : recalculables. Les tables se lisent par lots (`BATCH_ROWS`) et s'écrivent au
fil dans l'entrée du zip. Les journaux ne disent que des identifiants, des nombres et la durée."""

import asyncio
import json
import logging
import os
import tempfile
import time
import zipfile
from collections.abc import AsyncIterator
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
BATCH_ROWS = (
    500  # lignes lues puis écrites à la fois : la mémoire d'une table ne dépend pas de sa taille
)


def export_filename(now: datetime, zone: ZoneInfo) -> str:
    """`tremplin-export-AAAAMMJJ.zip`, le jour étant celui de l'utilisatrice."""
    return f"tremplin-export-{now.astimezone(zone):%Y%m%d}.zip"


def export_lock(locks: KeyLocks, user_id: str) -> asyncio.Lock:
    """Un export à la fois par compte : un second appel attend la fin du premier."""
    return locks.get(user_id, "export")


async def user_export_zone(db: AsyncSession, user_id: str) -> ZoneInfo:
    """Le fuseau de ses réglages (`Europe/Paris` si inconnu)."""
    return user_zone((await SettingsService(db, user_id).get()).timezone)


def _entry(name: str, now: datetime) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=now.astimezone(UTC).timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    return info


def _encode(rows: list[dict[str, Any]], *, first: bool) -> bytes:
    """Un lot de lignes : une ligne JSON par ligne de table, séparées par des virgules."""
    lines = [json.dumps(row_json(row), ensure_ascii=False, default=json_default) for row in rows]
    sep = "\n" if first else ",\n"
    return (sep + ",\n".join(lines)).encode()


async def _write_table(
    zf: zipfile.ZipFile,
    name: str,
    batches: AsyncIterator[list[dict[str, Any]]],
    now: datetime,
) -> int:
    """`tables/<name>.json` : un tableau JSON écrit **au fil** des lots dans l'entrée du zip (une
    seule entrée ouverte, un lot en mémoire) ; rend le nombre de lignes écrites."""
    out = zf.open(_entry(f"tables/{name}.json", now), "w")
    count = 0
    try:
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
    """Les fichiers déposés ; un fichier effacé entre la liste et la lecture est laissé de côté."""
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
    """L'archive de `user_id`, prête à lire depuis le début. À fermer par l'appelant (le flux
    `stream_export` le fait)."""
    started = time.monotonic()
    # Fermé par `stream_export`, ou ici si la construction échoue.
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
        "Export des données : user=%s tables=%d rows=%d files=%d duration_ms=%d",
        user_id,
        len(counts),
        sum(counts.values()),
        files,
        int((time.monotonic() - started) * 1000),
    )
    return spool


def archive_size(spool: tempfile.SpooledTemporaryFile[bytes]) -> int:
    """La taille de l'archive ; la lecture reprend au début."""
    size = spool.seek(0, os.SEEK_END)
    spool.seek(0)
    return size


async def stream_export(spool: tempfile.SpooledTemporaryFile[bytes]) -> AsyncIterator[bytes]:
    """L'archive par morceaux de 64 Kio ; le fichier est fermé à la fin ou si le client part."""
    try:
        while chunk := await asyncio.to_thread(spool.read, CHUNK_BYTES):
            yield chunk
    finally:
        spool.close()
