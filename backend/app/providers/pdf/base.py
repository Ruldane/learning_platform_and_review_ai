"""Ports du PDF : extraction du texte (fichier importé ou URL lue), rendu d'une page web en PDF
(repli des pages rendues en JavaScript), rendu de nos gabarits HTML (leçons, programme ; D89)
et mise en page d'un CV (positions, polices, couleurs, images des pages ; D119)."""

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


# Rendu d'un gabarit HTML (leçon avec schémas Mermaid, programme, CV) : 45 s au plus (D89).
HTML_RENDER_TIMEOUT_S = 45.0
_RESERVED = {"index.html", "footer.html", "header.html"}
# Nos fichiers figés (CSS, JS) et les polices jointes (noms « slugifiés » : `lato-400.ttf`).
_ASSET_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\.(css|js|woff2|ttf)")
# Une mesure en pouces (unité de Gotenberg) : « 8.27 », « 0 », « 0.6 ».
_INCHES = re.compile(r"\d{1,2}(\.\d{1,4})?")
_MAX_SIDE_IN = 20.0


@dataclass(frozen=True)
class PageSetup:
    """Taille de la page et marges (haut, droite, bas, gauche) en pouces, telles que Gotenberg
    les lit ; le gabarit d'un CV suit la page du PDF d'origine, marges nulles (la mise en page
    est dans le CSS)."""

    width_in: str
    height_in: str
    margins_in: tuple[str, str, str, str] = ("0", "0", "0", "0")

    def __post_init__(self) -> None:
        for value in (self.width_in, self.height_in, *self.margins_in):
            if not _INCHES.fullmatch(value):
                raise ValueError("mesure de page refusée")
        # Côté dans ]0 ; 20] pouces (`MAX_PAGE_SIDE_PT`), marge sous la moitié de son côté.
        width, height = float(self.width_in), float(self.height_in)
        top, right, bottom, left = (float(value) for value in self.margins_in)
        if not (0 < width <= _MAX_SIDE_IN and 0 < height <= _MAX_SIDE_IN):
            raise ValueError("mesure de page refusée")
        if max(top, bottom) * 2 >= height or max(left, right) * 2 >= width:
            raise ValueError("mesure de page refusée")


@dataclass(frozen=True)
class HtmlDocument:
    """Page à rendre : `index.html`, ressources jointes à côté (noms simples, CSS, JS ou police :
    nos fichiers figés et les polices libres), pied de page (`pageNumber`, `totalPages`),
    expression attendue avant l'impression (`waitForExpression`) et page (`None` : A4, marges de
    0,6 pouce, comme les leçons)."""

    index_html: str
    assets: Mapping[str, bytes]
    footer_html: str | None = None
    wait_for_expression: str | None = None
    page: PageSetup | None = None

    def __post_init__(self) -> None:
        for name in self.assets:
            if name in _RESERVED or not _ASSET_NAME.fullmatch(name):
                raise ValueError("nom de ressource refusé")


class HtmlPdfRenderer(Protocol):
    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        """PDF de `document` (A4 ou `document.page`), en `timeout_s` au plus ; `RenderFailed`
        sinon."""
        ...


# Mise en page d'un CV (D119) : même sous-processus borné que l'extraction du texte (D72).
MAX_CV_PAGES = 4
# Profil LinkedIn exporté en PDF : souvent plus long qu'un CV ; borne de sûreté seulement.
MAX_LINKEDIN_PAGES = 40
LAYOUT_DPI = 72
LAYOUT_TIMEOUT_S = 60.0
# Sortie du worker (JSON, images PNG en base64) : 40 Mo au plus.
LAYOUT_MAX_OUTPUT_BYTES = 40 * 1024 * 1024
# Une page plus grande que 20 pouces de côté n'est pas une page de CV (et son image serait énorme).
MAX_PAGE_SIDE_PT = 1440
CV_TOO_LONG_MESSAGE = "Un CV de plus de 4 pages n'est pas pris en charge."
ROTATED_PAGE_MESSAGE = (
    "Une page de ce PDF est tournée : exporte-le de nouveau sans rotation, puis réessaie."
)


@dataclass(frozen=True)
class TextBlock:
    """Une ligne de mots de même police, taille et couleur. Coordonnées en points depuis le coin
    haut gauche de la page ; `color` en `#rrggbb` ; `invisible` : couleur proche du fond lu sur
    l'image de la page, taille sous 2 pt, ou hors de la page."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    font: str
    size: float
    color: str
    bold: bool
    invisible: bool


@dataclass(frozen=True)
class PageLayout:
    """Page en points ; blocs dans l'ordre du flux du contenu ; image PNG de la page à
    `LAYOUT_DPI` ; texte dans l'ordre du flux (ce que lit un parseur, texte invisible compris)."""

    width_pt: float
    height_pt: float
    blocks: list[TextBlock]
    image_png: bytes
    stream_text: str


@dataclass(frozen=True)
class PdfLayout:
    """`fonts` : polices du texte visible, sans préfixe de sous-ensemble (« ABCDEF+ »), de la
    plus employée à la moins employée ; `selectable` : au moins 20 caractères visibles sur la
    première page (un CV scanné ne l'est pas)."""

    pages: list[PageLayout]
    fonts: list[str]
    selectable: bool


class PdfLayoutExtractor(Protocol):
    async def extract_layout(self, data: bytes, *, max_pages: int = MAX_CV_PAGES) -> PdfLayout:
        """Mise en page des `MAX_CV_PAGES` pages au plus. `PdfUnreadable` : PDF protégé,
        endommagé, trop long à lire, page démesurée ou plus de `MAX_CV_PAGES` pages
        (`CV_TOO_LONG_MESSAGE`). Un PDF scanné rend des pages sans blocs, pas une erreur."""
        ...
