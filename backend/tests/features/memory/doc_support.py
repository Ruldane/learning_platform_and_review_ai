"""Matériel des tests de l'import de documents : DOCX réels (python-docx) et zips fabriqués à la
main (bombes), document en base prêt pour la chaîne d'ingestion."""

import io
import struct
import zipfile
from typing import Any

import docx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.db.models.memory import Document
from app.features.memory.repository import DocumentRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import source_hash

PHRASE = "Les transformeurs utilisent l'attention multi-têtes pour relier les mots."


def make_docx(
    paragraphs: list[str], *, heading: str | None = None, core_title: str | None = None
) -> bytes:
    document = docx.Document()
    if core_title is not None:
        document.core_properties.title = core_title
    if heading is not None:
        document.add_heading(heading, level=1)
    for text in paragraphs:
        document.add_paragraph(text)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def make_zip(entries: dict[str, bytes], *, stored: bool = False) -> bytes:
    """Zip en mémoire ; `stored` : sans compression (taux 1:1)."""
    out = io.BytesIO()
    method = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(out, "w", compression=method) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return out.getvalue()


async def add_document(
    factory: async_sessionmaker[AsyncSession],
    providers: MemoryProviders,
    user_id: str,
    *,
    kind: str,
    data: bytes | None = None,
    suffix: str = ".txt",
    **fields: Any,
) -> Document:
    """Document en base (commité), avec son fichier enregistré si `data` est donné."""
    key = None
    if data is not None:
        key = await providers.storage.save(user_id, "documents", data, suffix)
    values: dict[str, Any] = {
        "name": "cours.pdf",
        "source_kind": kind,
        "status": "queued",
        "storage_key": key,
        "size_bytes": len(data) if data is not None else None,
        "source_hash": source_hash(data or str(fields.get("url", "x")).encode()),
        **fields,
    }
    async with factory() as db:
        doc = await DocumentRepository(db, user_id).add(**values)
        await db.commit()
    return doc


async def reload(factory: async_sessionmaker[AsyncSession], user_id: str, doc_id: str) -> Document:
    async with factory() as db:
        doc = await DocumentRepository(db, user_id).get(doc_id)
    assert doc is not None
    return doc


def forge_size(data: bytes, name: str, size: int) -> bytes:
    """Zip dont l'entrée `name` déclare `size` octets décompressés dans son en-tête local ET dans
    le répertoire central (bombe qui ment sur sa taille)."""
    out = bytearray(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        offset = archive.getinfo(name).header_offset
    struct.pack_into("<I", out, offset + 22, size)  # en-tête local : taille décompressée
    central = out.find(b"PK\x01\x02")
    while central != -1:
        length = struct.unpack_from("<H", out, central + 28)[0]
        if bytes(out[central + 46 : central + 46 + length]) == name.encode():
            struct.pack_into("<I", out, central + 24, size)
        central = out.find(b"PK\x01\x02", central + 4)
    return bytes(out)


async def add_indexed_document(
    factory: async_sessionmaker[AsyncSession],
    providers: MemoryProviders,
    runtime: MemoryRuntime,
    user_id: str,
    *,
    title: str = "Cours NLP",
    text: str = PHRASE,
) -> str:
    """Document `indexed` dont l'élément (`kind="document"`, fragments, vecteurs) est écrit par le
    service, comme après l'ingestion ; rend l'identifiant du document."""
    doc = await add_document(factory, providers, user_id, kind="text", name=f"{title}.txt")
    async with factory() as db:
        out = await MemoryService(db, user_id, runtime).write(
            WriteDraft(kind="document", title=title, text=text, author="user", reason=None)
        )
        stored = await DocumentRepository(db, user_id).get(doc.id)
        assert stored is not None
        stored.status, stored.item_id = "indexed", out.item.id
        await db.commit()
    return doc.id
