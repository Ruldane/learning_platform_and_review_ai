"""Mise en page d'un CV (D119), sans service externe : `pypdfium2` ouvre le PDF, compte les pages,
rend l'image de chaque page et lit le texte dans l'ordre du flux ; `pdfplumber` donne chaque
caractère avec sa position, sa police, sa taille et sa couleur.

N'importe ni FastAPI ni la base (le worker `layout_worker` l'importe seul, D72) : le résultat est
un dictionnaire prêt pour JSON, que `layout.parse_layout` relit en `PdfLayout`."""

import base64
import io
import math
import re
from collections import Counter
from typing import Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image

SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_BOLD = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
# Sous 2 pt, un texte est illisible : invisible.
MIN_VISIBLE_SIZE = 2.0
# Une première page avec moins de 20 caractères visibles n'a pas de texte sélectionnable.
SELECTABLE_MIN_CHARS = 20
# Couleur du texte proche du fond : écart au plus de 24 (sur 255) sur chaque canal.
SAME_COLOR_MAX_DELTA = 24

Rgb = tuple[int, int, int]
Char = dict[str, Any]


class TooManyPages(Exception):
    """Plus de pages que le plafond d'un CV."""


class PageTooLarge(Exception):
    """Page démesurée (son image ne serait pas une page de CV)."""


def clean_font_name(name: str) -> str:
    """Nom de police sans préfixe de sous-ensemble (« ABCDEF+Lato-Bold » → « Lato-Bold »)."""
    return SUBSET_PREFIX.sub("", name)


def _rgb(color: object) -> Rgb:
    """Couleur de remplissage de pdfplumber (gris, RVB ou CMJN, de 0 à 1) en RVB 0..255 ; noir
    pour un motif ou une couleur absente."""
    if not isinstance(color, tuple | list) or not all(
        isinstance(part, int | float) for part in color
    ):
        return (0, 0, 0)
    parts = [min(max(float(part), 0.0), 1.0) for part in color]
    if len(parts) == 1:
        parts = parts * 3
    elif len(parts) == 4:
        cyan, magenta, yellow, black = parts
        parts = [(1 - cyan) * (1 - black), (1 - magenta) * (1 - black), (1 - yellow) * (1 - black)]
    elif len(parts) != 3:
        return (0, 0, 0)
    red, green, blue = (round(part * 255) for part in parts)
    return (red, green, blue)


def _attrs(char: Char) -> tuple[str, float, Rgb]:
    return (str(char["fontname"]), round(float(char["size"]), 1), _rgb(char["non_stroking_color"]))


def _continues(line: list[Char], char: Char) -> bool:
    """Même ligne de mots : mêmes police, taille et couleur, même hauteur, juste à droite."""
    last = line[-1]
    if _attrs(char) != _attrs(last):
        return False
    size = float(last["size"]) or 1.0
    gap = float(char["x0"]) - float(last["x1"])
    same_row = abs(float(char["top"]) - float(last["top"])) <= max(1.0, size * 0.2)
    return same_row and -size * 0.25 <= gap <= size


def _text(line: list[Char]) -> str:
    """Texte de la ligne ; un blanc est ajouté là où les lettres s'écartent sans espace écrit."""
    parts: list[str] = []
    previous: Char | None = None
    for char in line:
        if previous is not None and float(char["x0"]) - float(previous["x1"]) > 0.15 * float(
            char["size"]
        ):
            parts.append(" ")
        parts.append(str(char["text"]))
        previous = char
    text = " ".join("".join(parts).split())
    # Un caractère isolé hors Unicode valide (surrogate) ne doit pas suivre jusqu'au JSON.
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _lines(chars: list[Char]) -> list[list[Char]]:
    """Caractères dans l'ordre du flux, regroupés en lignes de mots (une ligne = un bloc)."""
    lines: list[list[Char]] = []
    for char in chars:
        if lines and _continues(lines[-1], char):
            lines[-1].append(char)
        else:
            lines.append([char])
    return lines


def _background(image: Image.Image, box: tuple[float, float, float, float], scale: float) -> Rgb:
    """Couleur dominante de l'image sous le bloc (le fond : les lettres n'en couvrent qu'une
    partie) ; blanc si la zone est vide."""
    x0, top, x1, bottom = box
    left, upper = max(math.floor(x0 * scale), 0), max(math.floor(top * scale), 0)
    right = min(math.ceil(x1 * scale), image.width)
    lower = min(math.ceil(bottom * scale), image.height)
    if right <= left or lower <= upper:
        return (255, 255, 255)
    crop = image.crop((left, upper, right, lower))
    colors = crop.getcolors(maxcolors=crop.width * crop.height)
    if not colors:
        return (255, 255, 255)
    _count, dominant = max(colors, key=lambda item: item[0])
    if not isinstance(dominant, tuple):  # image RVB : jamais un indice de palette
        return (255, 255, 255)
    return (int(dominant[0]), int(dominant[1]), int(dominant[2]))


def _block(
    line: list[Char], image: Image.Image, page_size: tuple[float, float], scale: float
) -> list[Any]:
    first = line[0]
    box = (
        min(float(char["x0"]) for char in line),
        min(float(char["top"]) for char in line),
        max(float(char["x1"]) for char in line),
        max(float(char["bottom"]) for char in line),
    )
    width, height = page_size
    size = float(first["size"])
    color = _rgb(first["non_stroking_color"])
    background = _background(image, box, scale)
    off_page = box[2] <= 0 or box[0] >= width or box[3] <= 0 or box[1] >= height
    blended = max(abs(a - b) for a, b in zip(color, background, strict=True))
    invisible = size < MIN_VISIBLE_SIZE or off_page or blended <= SAME_COLOR_MAX_DELTA
    font = clean_font_name(str(first["fontname"]))
    return [
        _text(line),
        *(round(value, 2) for value in box),
        font,
        round(size, 2),
        "#{:02x}{:02x}{:02x}".format(*color),
        bool(_BOLD.search(font)),
        invisible,
    ]


def _page_blocks(page: Any, image: Image.Image, scale: float) -> list[list[Any]]:
    size = (float(page.width), float(page.height))
    blocks = [_block(line, image, size, scale) for line in _lines(list(page.chars))]
    return [block for block in blocks if block[0]]


def _png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _render(
    data: bytes, max_pages: int, dpi: int, max_side: float
) -> list[tuple[Image.Image, str]]:
    """Image (RVB) et texte du flux de chaque page, par PDFium. Lève `TooManyPages`,
    `PageTooLarge`, ou l'erreur de PDFium (protégé, endommagé, pas un PDF)."""
    document = pdfium.PdfDocument(data)
    try:
        count = len(document)
        if count > max_pages:
            raise TooManyPages()
        if count == 0:
            raise ValueError("aucune page")
        pages: list[tuple[Image.Image, str]] = []
        for index in range(count):
            page = document[index]
            width, height = page.get_size()
            if width > max_side or height > max_side:
                raise PageTooLarge()
            image = page.render(scale=dpi / 72).to_pil().convert("RGB")
            stream = page.get_textpage().get_text_range().replace("\r\n", "\n")
            pages.append((image, stream.encode("utf-8", errors="replace").decode("utf-8")))
        return pages
    finally:
        document.close()


def _fonts(pages: list[dict[str, Any]]) -> list[str]:
    counts: Counter[str] = Counter()
    for page in pages:
        for block in page["blocks"]:
            if not block[-1]:
                counts[block[5]] += len(block[0].replace(" ", ""))
    return [name for name, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def extract_layout_payload(
    data: bytes, max_pages: int, dpi: int, max_side: float
) -> dict[str, Any]:
    """Mise en page des pages du PDF (au plus `max_pages`), en dictionnaire prêt pour JSON :
    `pages` (`width`, `height`, `blocks` en listes `[texte, x0, top, x1, bottom, police, taille,
    couleur, gras, invisible]`, `png` en base64, `stream`), `fonts`, `selectable`."""
    rendered = _render(data, max_pages, dpi, max_side)
    scale = dpi / 72
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(data), pages=list(range(1, len(rendered) + 1))) as pdf:
        for page, (image, stream) in zip(pdf.pages, rendered, strict=True):
            pages.append(
                {
                    "width": round(float(page.width), 2),
                    "height": round(float(page.height), 2),
                    "blocks": _page_blocks(page, image, scale),
                    "png": _png(image),
                    "stream": stream,
                }
            )
            page.close()
    visible = sum(len(b[0].replace(" ", "")) for b in pages[0]["blocks"] if not b[-1])
    return {"pages": pages, "fonts": _fonts(pages), "selectable": visible >= SELECTABLE_MIN_CHARS}
