"""Mise en page d'un CV (D119), sans service externe : `pypdfium2` ouvre le PDF, compte les pages,
rend l'image de chaque page dans sa CropBox et lit le texte dans l'ordre du flux ; `pdfplumber`
donne chaque caractère avec sa position, sa police, sa taille et sa couleur ; l'encre lue sur
l'image (`layout_ink`) dit si un bloc est visible.

Un seul repère, celui de l'image : points depuis le coin haut gauche de la CropBox (1 pixel =
1 point à 72 dpi). pdfplumber donne `x0` dans l'espace de la page et `y0`/`y1` depuis le bas de la
MediaBox : ils sont ramenés à la CropBox lue par PDFium (revue 6.3, I3).

N'importe ni FastAPI ni la base (le worker `layout_worker` l'importe seul, D72) : le résultat est
un dictionnaire prêt pour JSON, que `layout.parse_layout` relit en `PdfLayout`."""

import base64
import io
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image

from app.providers.pdf.layout_ink import Pixels, Rgb, measure_ink, pixels_of

SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_BOLD = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
# Sous 2 pt, un texte est illisible : invisible.
MIN_VISIBLE_SIZE = 2.0
# Lettres écrasées (`Tz`) : avance moyenne sous 15 % de la taille (revue 6.3, M3).
MIN_ADVANCE_RATIO = 0.15
# Une première page avec moins de 20 caractères visibles n'a pas de texte sélectionnable.
SELECTABLE_MIN_CHARS = 20
# Plus de blocs que cela pour tout le document : pas un CV (revue 6.3, I4 ; un CV en a < 300).
MAX_LAYOUT_BLOCKS = 5000
# Espaces dont pdfplumber rend les composantes telles quelles (gris, RVB, CMJN) ; ailleurs
# (`Separation`, `DeviceN`, `Indexed`, `Lab`, motif), la couleur est lue sur l'image (I2).
_DEVICE_SPACES = {"DeviceGray", "DeviceRGB", "DeviceCMYK", "CalGray", "CalRGB", "ICCBased"}

Char = dict[str, Any]


class TooManyPages(Exception):
    """Plus de pages que le plafond d'un CV."""


class PageTooLarge(Exception):
    """Page démesurée (son image ne serait pas une page de CV)."""


class RotatedPage(Exception):
    """Page tournée avec du texte : ses positions n'ont pas le repère de son image (revue 6.3,
    M1) ; le refus invite à exporter le PDF sans rotation (D124)."""


class TooManyBlocks(Exception):
    """Plus de `MAX_LAYOUT_BLOCKS` blocs : PDF refusé comme illisible."""


@dataclass(frozen=True)
class _Frame:
    """CropBox (espace de la page) et bas de la MediaBox, lus par PDFium ; taille de l'image."""

    left: float
    top: float
    media_bottom: float
    width: float
    height: float


def clean_font_name(name: str) -> str:
    """Nom de police sans préfixe de sous-ensemble (« ABCDEF+Lato-Bold » → « Lato-Bold »)."""
    return SUBSET_PREFIX.sub("", name)


def _rgb(color: object) -> Rgb | None:
    """Composantes de pdfplumber (gris, RVB ou CMJN, de 0 à 1) en RVB 0..255 ; `None` sinon."""
    if not isinstance(color, tuple | list) or not all(
        isinstance(part, int | float) for part in color
    ):
        return None
    parts = [min(max(float(part), 0.0), 1.0) for part in color]
    if len(parts) == 1:
        parts = parts * 3
    elif len(parts) == 4:
        cyan, magenta, yellow, black = parts
        parts = [(1 - cyan) * (1 - black), (1 - magenta) * (1 - black), (1 - yellow) * (1 - black)]
    elif len(parts) != 3:
        return None
    red, green, blue = (round(part * 255) for part in parts)
    return (red, green, blue)


def _attrs(char: Char) -> tuple[str, float, object]:
    color = char["non_stroking_color"]
    return (str(char["fontname"]), round(float(char["size"]), 1), str(color))


def _continues(line: list[Char], char: Char) -> bool:
    """Même ligne de mots : mêmes police, taille et couleur, même hauteur, juste à droite."""
    last = line[-1]
    if _attrs(char) != _attrs(last):
        return False
    size = float(last["size"]) or 1.0
    gap = float(char["x0"]) - float(last["x1"])
    same_row = abs(float(char["y1"]) - float(last["y1"])) <= max(1.0, size * 0.2)
    return same_row and -size * 0.25 <= gap <= size


def _text(line: list[Char]) -> str:
    """Texte de la ligne ; un blanc est ajouté là où les lettres s'écartent sans espace écrit."""
    parts: list[str] = []
    previous: Char | None = None
    for char in line:
        gap = float(char["x0"]) - float(previous["x1"]) if previous is not None else 0.0
        if gap > 0.15 * float(char["size"]):
            parts.append(" ")
        parts.append(str(char["text"]))
        previous = char
    text = " ".join("".join(parts).split())
    # Un caractère isolé hors Unicode valide (surrogate) ne doit pas suivre jusqu'au JSON.
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _lines(chars: list[Char], budget: int) -> list[list[Char]]:
    """Caractères dans l'ordre du flux, regroupés en lignes de mots (une ligne = un bloc) ;
    `TooManyBlocks` dès que `budget` est dépassé."""
    lines: list[list[Char]] = []
    for char in chars:
        if lines and _continues(lines[-1], char):
            lines[-1].append(char)
            continue
        if len(lines) >= budget:
            raise TooManyBlocks()
        lines.append([char])
    return lines


def _box(line: list[Char], frame: _Frame) -> tuple[float, float, float, float]:
    """Cadre de la ligne dans le repère de l'image (CropBox, origine en haut à gauche)."""
    return (
        min(float(char["x0"]) for char in line) - frame.left,
        frame.top - (max(float(char["y1"]) for char in line) + frame.media_bottom),
        max(float(char["x1"]) for char in line) - frame.left,
        frame.top - (min(float(char["y0"]) for char in line) + frame.media_bottom),
    )


def _mostly_off_page(box: tuple[float, float, float, float], frame: _Frame) -> bool:
    """Moins de la moitié du cadre, en largeur ou en hauteur, dans la page (revue 6.3, M2)."""
    x0, top, x1, bottom = box
    inside_x = min(x1, frame.width) - max(x0, 0.0)
    inside_y = min(bottom, frame.height) - max(top, 0.0)
    return inside_x < (x1 - x0) / 2 or inside_y < (bottom - top) / 2 or inside_x <= 0


def _block(line: list[Char], pixels: Pixels, frame: _Frame, scale: float) -> list[Any]:
    first = line[0]
    text = _text(line)
    box = _box(line, frame)
    size = float(first["size"])
    ink = measure_ink(pixels, box, scale)
    squeezed = (box[2] - box[0]) / max(len(text), 1) < MIN_ADVANCE_RATIO * size
    invisible = (
        size < MIN_VISIBLE_SIZE or _mostly_off_page(box, frame) or squeezed or not ink.visible
    )
    declared = _rgb(first["non_stroking_color"])
    trusted = str(first.get("ncs")) in _DEVICE_SPACES and declared is not None
    color = declared if trusted else ink.color
    font = clean_font_name(str(first["fontname"]))
    return [
        text,
        *(round(value, 2) for value in box),
        font,
        round(size, 2),
        "#{:02x}{:02x}{:02x}".format(*(color or (0, 0, 0))),
        bool(_BOLD.search(font)),
        invisible,
    ]


def _page_blocks(
    page: Any, image: Image.Image, frame: _Frame, budget: int
) -> tuple[list[list[Any]], int]:
    """Blocs non vides de la page, et nombre de lignes comptées contre le plafond."""
    pixels = pixels_of(image)
    scale = image.width / frame.width
    lines = _lines(list(page.chars), budget)
    blocks = [_block(line, pixels, frame, scale) for line in lines]
    return [block for block in blocks if block[0]], len(lines)


def _png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _render_page(page: Any, dpi: int, max_side: float) -> tuple[Image.Image, str, _Frame]:
    width, height = page.get_size()
    if width > max_side or height > max_side:
        raise PageTooLarge()
    textpage = page.get_textpage()
    if page.get_rotation() and textpage.count_chars():
        # Une page tournée avec du texte n'a pas le repère de son image (revue 6.3, M1).
        raise RotatedPage()
    left, _bottom, _right, top = page.get_cropbox()
    frame = _Frame(left, top, page.get_mediabox()[1], width, height)
    image = page.render(scale=dpi / 72).to_pil().convert("RGB")
    if abs(image.width - width * dpi / 72) > 1 or abs(image.height - height * dpi / 72) > 1:
        raise ValueError("image et page discordantes")
    stream = textpage.get_text_range().replace("\r\n", "\n")
    return image, stream.encode("utf-8", errors="replace").decode("utf-8"), frame


def _render(
    data: bytes, max_pages: int, dpi: int, max_side: float
) -> list[tuple[Image.Image, str, _Frame]]:
    """Image (RVB), texte du flux et repère de chaque page, par PDFium. Lève `TooManyPages`,
    `PageTooLarge`, `RotatedPage`, ou une erreur (protégé, endommagé, pas un PDF)."""
    document = pdfium.PdfDocument(data)
    try:
        count = len(document)
        if count > max_pages:
            raise TooManyPages()
        if count == 0:
            raise ValueError("aucune page")
        return [_render_page(document[index], dpi, max_side) for index in range(count)]
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
    """Mise en page des pages du PDF (au plus `max_pages`, `MAX_LAYOUT_BLOCKS` blocs en tout), en
    dictionnaire prêt pour JSON : `pages` (`width`, `height` de la CropBox, `blocks` en listes
    `[texte, x0, top, x1, bottom, police, taille, couleur, gras, invisible]`, `png` en base64,
    `stream`), `fonts`, `selectable`."""
    rendered = _render(data, max_pages, dpi, max_side)
    pages: list[dict[str, Any]] = []
    budget = MAX_LAYOUT_BLOCKS
    with pdfplumber.open(io.BytesIO(data), pages=list(range(1, len(rendered) + 1))) as pdf:
        for page, (image, stream, frame) in zip(pdf.pages, rendered, strict=True):
            blocks, counted = _page_blocks(page, image, frame, budget)
            budget -= counted
            pages.append(
                {
                    "width": round(frame.width, 2),
                    "height": round(frame.height, 2),
                    "blocks": blocks,
                    "png": _png(image),
                    "stream": stream,
                }
            )
            page.close()
    visible = sum(len(b[0].replace(" ", "")) for b in pages[0]["blocks"] if not b[-1])
    return {"pages": pages, "fonts": _fonts(pages), "selectable": visible >= SELECTABLE_MIN_CHARS}
