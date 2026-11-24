"""Contract of an ingestion source: from the stored document (stored file or link) to raw text
and its title. No source logs a file name, a link or any content."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import AppError
from app.db.models.memory import DocumentSourceKind
from app.providers.pdf.base import PdfTextExtractor
from app.providers.storage.base import FileStorage
from app.providers.web.base import WebReader, YoutubeTranscripts


@dataclass(frozen=True)
class SourceInput:
    document_id: str
    user_id: str
    name: str
    url: str | None
    storage_key: str | None
    tags: tuple[str, ...] = ()  # the document's tags, carried over to its item (D124)
    sync_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ExtractionTools:
    storage: FileStorage
    pdf: PdfTextExtractor
    web: WebReader
    youtube: YoutubeTranscripts


@dataclass(frozen=True)
class Extracted:
    title: str
    text: str
    lang: str | None = None


class SourceExtractor(Protocol):
    kind: DocumentSourceKind

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted: ...


def _missing() -> AppError:
    return AppError(
        "document_source_missing",
        "Original file or link not found: import this document again.",
        422,
    )


async def read_stored(source: SourceInput, tools: ExtractionTools) -> bytes:
    """Bytes of the stored file, read for the document's owner (`read(user_id, key)` rejects
    another user's key). Missing file: readable error, which a new import repairs (it rewrites
    the file)."""
    if source.storage_key is None:
        raise _missing()
    try:
        return await tools.storage.read(source.user_id, source.storage_key)
    except FileNotFoundError:
        raise _missing() from None


def required_url(source: SourceInput) -> str:
    if source.url is None:
        raise _missing()
    return source.url


def stem(name: str) -> str:
    """Name without its extension ("course.v2.pdf" → "course.v2"); the whole name if it has none."""
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def decode_text(data: bytes) -> str:
    """UTF-8 (BOM removed); already checked on import, an invalid byte is replaced."""
    return data.decode("utf-8-sig", errors="replace")
