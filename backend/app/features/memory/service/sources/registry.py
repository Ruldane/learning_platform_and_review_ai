"""Registry of ingestion sources. Adding a source: one module in this package and one line
here (the key is its `DocumentSourceKind`)."""

from typing import cast

from app.core.errors import AppError
from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import SourceExtractor
from app.features.memory.service.sources.docx import DocxSource
from app.features.memory.service.sources.markdown import MarkdownSource
from app.features.memory.service.sources.paste import PasteSource
from app.features.memory.service.sources.pdf import PdfSource
from app.features.memory.service.sources.text import TextSource
from app.features.memory.service.sources.url import UrlSource
from app.features.memory.service.sources.youtube import YoutubeSource

INGESTION_SOURCES: dict[DocumentSourceKind, SourceExtractor] = {
    "pdf": PdfSource(),
    "docx": DocxSource(),
    "markdown": MarkdownSource(),
    "text": TextSource(),
    "url": UrlSource(),
    "youtube": YoutubeSource(),
    "paste": PasteSource(),
}


def get_source(kind: str) -> SourceExtractor:
    """Source for the kind; an unknown kind (corrupted database row) is an internal error whose
    message does not echo the value."""
    source = INGESTION_SOURCES.get(cast(DocumentSourceKind, kind))
    if source is None:
        raise AppError("unknown_source_kind", "Unknown document source kind.", 500)
    return source
