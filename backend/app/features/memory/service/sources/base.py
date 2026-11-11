"""Contrat d'une source d'ingestion : du document en base (fichier stocké ou lien) au texte brut
et à son titre. Aucune source ne journalise un nom de fichier, un lien ni un contenu."""

from dataclasses import dataclass
from typing import Protocol

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
        "Fichier ou lien d'origine introuvable : importe ce document de nouveau.",
        422,
    )


async def read_stored(source: SourceInput, tools: ExtractionTools) -> bytes:
    """Octets du fichier enregistré, lus pour le propriétaire du document (`read(user_id, key)`
    refuse la clé d'un autre utilisateur). Fichier disparu : erreur lisible, qu'un nouvel
    import répare (il réécrit le fichier)."""
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
    """Nom sans son extension (« cours.v2.pdf » → « cours.v2 ») ; le nom entier s'il n'en a pas."""
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def decode_text(data: bytes) -> str:
    """UTF-8 (BOM retiré) ; déjà vérifié à l'import, un octet invalide est remplacé."""
    return data.decode("utf-8-sig", errors="replace")
