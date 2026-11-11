"""Import des documents (14.2) : un fichier, un lien ou un texte collé devient une ligne
`documents` en file, que le worker ingère. Le nom reçu n'est qu'un nom d'affichage nettoyé ; le
fichier est enregistré sous une clé générée (`<user_id>/documents/<uuid4><suffixe canonique>`).
Ni les messages ni les journaux ne citent un nom de fichier, un lien ou un contenu."""

import builtins
import logging
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.db.models.memory import Document, DocumentSourceKind, MemoryItem
from app.features.memory.repository import DocumentRepository
from app.features.memory.schemas import DocumentError, DocumentOut
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import (
    clean_display,
    clean_text,
    display_name,
    source_hash,
)
from app.features.memory.service.upload import (
    MAX_PASTE_CHARS,
    MAX_UPLOAD_BYTES,
    SUFFIX_OF,
    classify_url,
    detect_upload,
    file_too_large,
    normalize_url,
)
from app.providers.web.base import youtube_video_id

logger = logging.getLogger(__name__)

LIST_LIMIT = 200
READ_BLOCK = 1024 * 1024
STORAGE_CATEGORY = "documents"


@dataclass(frozen=True)
class _Incoming:
    """Document à créer, avant son insertion. `data` : octets à enregistrer (fichier ou texte
    collé), `None` pour un lien."""

    kind: DocumentSourceKind
    name: str
    digest: str
    data: bytes | None = None
    suffix: str | None = None
    url: str | None = None


def default_paste_title() -> str:
    return f"Texte collé du {date.today():%d/%m/%Y}"


def invalid_source() -> AppError:
    return AppError(
        "invalid_document_source", "Fournis un fichier, un lien ou un texte (un seul).", 422
    )


def to_document_out(doc: Document) -> DocumentOut:
    error = DocumentError.model_validate(doc.error) if doc.error else None
    return DocumentOut.model_validate(
        {
            "id": doc.id,
            "name": doc.name,
            "source_kind": doc.source_kind,
            "status": doc.status,
            "error": error,
            "url": doc.url,
            "size_bytes": doc.size_bytes,
            "item_id": doc.item_id,
            "learned": doc.learned,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }
    )


async def _read_upload(file: UploadFile) -> bytes:
    """Lecture par blocs ; au-delà de `MAX_UPLOAD_BYTES`, 413 (exactement 20 Mo passe)."""
    blocks: list[bytes] = []
    size = 0
    while block := await file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_UPLOAD_BYTES:
            raise file_too_large()
        blocks.append(block)
    return b"".join(blocks)


def _from_url(raw: str) -> _Incoming:
    url = normalize_url(raw)
    kind = classify_url(url)
    video = youtube_video_id(url)
    name = f"Vidéo YouTube {video}" if video else (urlsplit(url).hostname or "")
    return _Incoming(kind, display_name(name), source_hash(f"url:{url}".encode()), url=url)


def _from_text(text: str, title: str | None) -> _Incoming:
    if len(text) > MAX_PASTE_CHARS:
        raise AppError("paste_too_long", "Texte trop long : 500 000 caractères au maximum.", 422)
    cleaned = clean_text(text)
    name = clean_display(title) or default_paste_title()
    data = cleaned.encode("utf-8")
    digest = source_hash(f"text:{cleaned}".encode())
    return _Incoming("paste", name, digest, data=data, suffix=SUFFIX_OF["text"])


class DocumentService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: MemoryRuntime) -> None:
        self._db = db
        self._user_id = user_id
        self._runtime = runtime
        self._docs = DocumentRepository(db, user_id)

    async def create(
        self, *, file: UploadFile | None, url: str | None, text: str | None, title: str | None
    ) -> tuple[DocumentOut, bool]:
        """(document, nouveau ?). Exactement une source. Même contenu déjà importé : l'existant,
        sauf s'il est en erreur ou bloqué, auquel cas il repart en file (`_again`). Le commit
        précède la mise en file du worker (qui doit voir la ligne)."""
        url = url.strip() if url and url.strip() else None
        text = text if text and text.strip() else None
        if [file is not None, url is not None, text is not None].count(True) != 1:
            raise invalid_source()
        incoming = await self._incoming(file, url, text, title)
        existing = await self._docs.find_by_source_hash(incoming.digest)
        if existing is not None:
            return await self._again(existing, incoming)
        doc, created = await self._insert(incoming)
        if not created:  # course perdue : un import identique a gagné
            return to_document_out(doc), False
        self._runtime.jobs.enqueue_ingest(self._user_id, doc.id)
        logger.info("Document %s en file (%s)", doc.id, doc.source_kind)
        return to_document_out(doc), True

    async def _incoming(
        self, file: UploadFile | None, url: str | None, text: str | None, title: str | None
    ) -> _Incoming:
        if url is not None:
            return _from_url(url)
        if text is not None:
            return _from_text(text, title)
        assert file is not None
        data = await _read_upload(file)
        kind = detect_upload(file.filename, data)
        name = display_name(file.filename)
        return _Incoming(kind, name, source_hash(data), data=data, suffix=SUFFIX_OF[kind])

    async def _again(self, existing: Document, incoming: _Incoming) -> tuple[DocumentOut, bool]:
        """Doublon rendu tel quel, sauf s'il est en erreur, ou en file ou en cours sans job prévu
        dans ce processus (statut final perdu) : il repart alors en file, erreur effacée, avec
        le fichier qu'on vient de recevoir (l'ancien est supprimé après le commit)."""
        stuck = existing.status in ("queued", "processing")
        stuck = stuck and not self._runtime.jobs.is_scheduled(existing.id)
        if existing.status != "error" and not stuck:
            return to_document_out(existing), False
        old_key, new_key = existing.storage_key, await self._save(incoming)
        if new_key is not None:
            existing.storage_key, existing.size_bytes = new_key, len(incoming.data or b"")
        existing.status, existing.error = "queued", None
        await self._commit_files(new_key, old_key if new_key is not None else None)
        self._runtime.jobs.enqueue_ingest(self._user_id, existing.id)
        logger.info("Document %s remis en file", existing.id)
        return to_document_out(existing), True

    async def _save(self, incoming: _Incoming) -> str | None:
        if incoming.data is None or incoming.suffix is None:
            return None
        storage = self._runtime.providers.storage
        return await storage.save(self._user_id, STORAGE_CATEGORY, incoming.data, incoming.suffix)

    async def _commit_files(self, new_key: str | None, old_key: str | None) -> None:
        """Commit ; s'il échoue, le nouveau fichier est supprimé, sinon l'ancien."""
        storage = self._runtime.providers.storage
        try:
            await self._db.commit()
        except BaseException:
            if new_key is not None:
                await storage.delete(self._user_id, new_key)
            raise
        if old_key is not None:
            await storage.delete(self._user_id, old_key)

    async def _insert(self, incoming: _Incoming) -> tuple[Document, bool]:
        """Fichier enregistré puis ligne insérée et validée ; tout échec supprime le fichier.
        Course sur le hash (unicité) : la transaction est annulée (elle ne contient que cette
        insertion, d'où aucun SAVEPOINT, D65 c) et le gagnant est rendu, `False`."""
        storage = self._runtime.providers.storage
        key = await self._save(incoming)
        committed = False
        try:
            doc = await self._docs.add(
                name=incoming.name,
                source_kind=incoming.kind,
                status="queued",
                url=incoming.url,
                storage_key=key,
                size_bytes=len(incoming.data) if incoming.data is not None else None,
                source_hash=incoming.digest,
            )
            await self._db.commit()
            committed = True
            return doc, True
        except IntegrityError:
            await self._db.rollback()
            winner = await self._docs.find_by_source_hash(incoming.digest)
            if winner is None:
                raise
            return winner, False
        finally:
            if key is not None and not committed:
                await storage.delete(self._user_id, key)

    async def mark_learned(self, document_id: str, runner: SessionRunner) -> str:
        """« Déjà appris » (D68) : lance le parcours `learned_document` sur un document indexé et
        pose `learned`. La session est lancée AVANT l'écriture du drapeau : elle ouvre ses propres
        sessions de base, la requête ne tient donc aucun verrou d'écriture pendant ce temps ; un
        refus de lancement laisse le drapeau intact. Relancer est sans danger : les acquis déjà
        écrits sont reconnus à leur titre."""
        doc = await self._docs.get(document_id)
        if doc is None:
            raise AppError("document_not_found", "Document introuvable.", 404)
        if doc.status != "indexed":
            raise AppError(
                "document_not_ready",
                "Le document doit être indexé avant d'être marqué déjà appris.",
                409,
            )
        session_id = await runner.start(
            self._user_id,
            "learned_document",
            {"document_id": doc.id},
            subject_type="document",
            subject_id=doc.id,
        )
        doc.learned = True
        await self._db.flush()
        logger.info("Document %s marqué déjà appris (session %s)", doc.id, session_id)
        return session_id

    async def list(self) -> list[DocumentOut]:
        return [to_document_out(doc) for doc in await self._docs.list_recent(LIST_LIMIT)]

    async def remove_for_item(self, item: MemoryItem) -> builtins.list[str]:
        """Suppression d'un élément `document` (appelée par `MemoryService.delete`, qui a vérifié
        que l'élément est à l'utilisateur) : ses lignes `documents` sont supprimées et les clés
        de leurs fichiers rendues, à supprimer après le commit."""
        docs = {doc.id: doc for doc in await self._docs.for_item(item.id)}
        if item.source_id is not None and item.source_id not in docs:
            linked = await self._docs.get(item.source_id)
            if linked is not None:
                docs[linked.id] = linked
        for doc in docs.values():
            await self._docs.delete(doc.id)
        return [doc.storage_key for doc in docs.values() if doc.storage_key is not None]
