"""Registre des sources d'ingestion. Ajouter une source : un module dans ce paquet et une ligne
ici (la clé est son `DocumentSourceKind`)."""

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
    """Source du type ; un type inconnu (ligne en base corrompue) est une erreur interne, dont le
    message ne recopie pas la valeur."""
    source = INGESTION_SOURCES.get(cast(DocumentSourceKind, kind))
    if source is None:
        raise AppError("unknown_source_kind", "Type de source de document inconnu.", 500)
    return source
