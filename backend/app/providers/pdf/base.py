"""Ports du PDF : extraction du texte (fichier importé ou URL lue), rendu d'une page web en PDF
(repli des pages rendues en JavaScript) et rendu de nos gabarits HTML (leçons, programme ; D89)."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError

MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 2_000_000

# Extraction en sous-processus (D72) : délai réel, mémoire bornée (POSIX), deux au plus à la fois.
PDF_TIMEOUT_S = 60.0
PDF_MAX_MEMORY_BYTES = 1024 * 1024 * 1024
PDF_TIMEOUT_MESSAGE = "PDF trop long à lire : délai dépassé."
_UNREADABLE_MESSAGE = "PDF illisible (protégé par mot de passe ou endommagé)."

# Rendu d'une page par Gotenberg : PDF de 20 Mo au plus, comme un PDF lu en ligne.
RENDER_MAX_BYTES = 20 * 1024 * 1024


class PdfUnreadable(AppError):
    """PDF chiffré, endommagé, trop long à lire ou qui n'est pas un PDF. Le message est toujours
    une constante de ce module : jamais le fichier ni son contenu."""

    def __init__(self, message: str = _UNREADABLE_MESSAGE) -> None:
        super().__init__("pdf_unreadable", message, status_code=422)


class PdfTextExtractor(Protocol):
    async def extract_text(self, data: bytes) -> str:
        """Texte des `MAX_PDF_PAGES` premières pages, tronqué à `MAX_TEXT_CHARS` caractères."""
        ...


class RenderFailed(AppError):
    """Rendu impossible (service en panne, délai, page refusée, corps trop gros). Ne cite jamais
    l'URL ni la réponse du service."""

    def __init__(self) -> None:
        super().__init__("render_failed", "Rendu de la page impossible.", status_code=502)


class PageRenderer(Protocol):
    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes:
        """PDF de la page à `url` (déjà validée par la garde SSRF), en `timeout_s` au plus."""
        ...


# Rendu d'un gabarit HTML (leçon avec schémas Mermaid, programme) : 45 s au plus (D89).
HTML_RENDER_TIMEOUT_S = 45.0
_RESERVED = {"index.html", "footer.html", "header.html"}
_ASSET_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\.(css|js)")


@dataclass(frozen=True)
class HtmlDocument:
    """Page à rendre : `index.html`, ressources jointes à côté (noms simples, CSS ou JS : nos
    fichiers figés seulement), pied de page (`pageNumber`, `totalPages`) et expression attendue
    avant l'impression (`waitForExpression`)."""

    index_html: str
    assets: Mapping[str, bytes]
    footer_html: str | None = None
    wait_for_expression: str | None = None

    def __post_init__(self) -> None:
        for name in self.assets:
            if name in _RESERVED or not _ASSET_NAME.fullmatch(name):
                raise ValueError("nom de ressource refusé")


class HtmlPdfRenderer(Protocol):
    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        """PDF A4 de `document`, en `timeout_s` au plus ; `RenderFailed` sinon."""
        ...
