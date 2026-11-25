"""Layout of a CV (D119), without an external service: `pypdfium2` opens the PDF, counts the pages,
renders the image of each page in its CropBox and reads the text in stream order; `pdfplumber`
gives each character with its position, font, size and colour; the ink read on the
image (`layout_ink`) says whether a block is visible.

A single frame of reference, that of the image: points from the top left corner of the CropBox
(1 pixel = 1 point at 72 dpi). pdfplumber gives `x0` in the page space and `y0`/`y1` from the bottom
of the MediaBox: they are brought back to the CropBox read by PDFium (review 6.3, I3).

Imports neither FastAPI nor the database (the `layout_worker` imports it alone, D72): the result is
a JSON-ready dictionary, which `layout.parse_layout` reads back into a `PdfLayout`."""

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
# Under 2 pt, a text is unreadable: invisible.
MIN_VISIBLE_SIZE = 2.0
# Squashed letters (`Tz`): average advance under 15% of the size (review 6.3, M3).
MIN_ADVANCE_RATIO = 0.15
# A first page with fewer than 20 visible characters has no selectable text.
SELECTABLE_MIN_CHARS = 20
# More blocks than this for the whole document: not a CV (review 6.3, I4; a CV has < 300).
MAX_LAYOUT_BLOCKS = 5000
# Spaces whose components pdfplumber returns as they are (grey, RGB, CMYK); elsewhere
# (`Separation`, `DeviceN`, `Indexed`, `Lab`, pattern), the colour is read from the image (I2).
_DEVICE_SPACES = {"DeviceGray", "DeviceRGB", "DeviceCMYK", "CalGray", "CalRGB", "ICCBased"}

Char = dict[str, Any]


class TooManyPages(Exception):
    """More pages than a CV's cap."""


class PageTooLarge(Exception):
    """Oversized page (its image would not be a CV page)."""


class RotatedPage(Exception):
    """Rotated page with text: its positions do not share the frame of its image (review 6.3,
    M1); the refusal invites exporting the PDF without rotation (D124)."""


class TooManyBlocks(Exception):
    """More than `MAX_LAYOUT_BLOCKS` blocks: PDF refused as unreadable."""


@dataclass(frozen=True)
class _Frame:
    """CropBox (page space) and bottom of the MediaBox, read by PDFium; image size."""

    left: float
    top: float
    media_bottom: float
    width: float
    height: float


def clean_font_name(name: str) -> str:
    """Font name without subset prefix ("ABCDEF+Lato-Bold" -> "Lato-Bold")."""
    return SUBSET_PREFIX.sub("", name)


def _rgb(color: object) -> Rgb | None:
    """pdfplumber components (grey, RGB or CMYK, from 0 to 1) as RGB 0..255; `None` otherwise."""
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
    """Same line of words: same font, size and colour, same height, just to the right."""
    last = line[-1]
    if _attrs(char) != _attrs(last):
        return False
    size = float(last["size"]) or 1.0
    gap = float(char["x0"]) - float(last["x1"])
    same_row = abs(float(char["y1"]) - float(last["y1"])) <= max(1.0, size * 0.2)
    return same_row and -size * 0.25 <= gap <= size


def _text(line: list[Char]) -> str:
    """Text of the line; a blank is added where the letters spread apart without a written space."""
    parts: list[str] = []
    previous: Char | None = None
    for char in line:
        gap = float(char["x0"]) - float(previous["x1"]) if previous is not None else 0.0
        if gap > 0.15 * float(char["size"]):
            parts.append(" ")
        parts.append(str(char["text"]))
        previous = char
    text = " ".join("".join(parts).split())
    # A lone character outside valid Unicode (surrogate) must not travel on to the JSON.
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _lines(chars: list[Char], budget: int) -> list[list[Char]]:
    """Characters in stream order, grouped into lines of words (one line = one block);
    `TooManyBlocks` as soon as `budget` is exceeded."""
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
    """Frame of the line in the image's frame of reference (CropBox, origin at the top left)."""
    return (
        min(float(char["x0"]) for char in line) - frame.left,
        frame.top - (max(float(char["y1"]) for char in line) + frame.media_bottom),
        max(float(char["x1"]) for char in line) - frame.left,
        frame.top - (min(float(char["y0"]) for char in line) + frame.media_bottom),
    )


def _mostly_off_page(box: tuple[float, float, float, float], frame: _Frame) -> bool:
    """Less than half of the frame, in width or in height, inside the page (review 6.3, M2)."""
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
    """Non-empty blocks of the page, and the number of lines counted against the cap."""
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
        # A rotated page with text does not share the frame of its image (review 6.3, M1).
        raise RotatedPage()
    left, _bottom, _right, top = page.get_cropbox()
    frame = _Frame(left, top, page.get_mediabox()[1], width, height)
    image = page.render(scale=dpi / 72).to_pil().convert("RGB")
    if abs(image.width - width * dpi / 72) > 1 or abs(image.height - height * dpi / 72) > 1:
        raise ValueError("image and page do not match")
    stream = textpage.get_text_range().replace("\r\n", "\n")
    return image, stream.encode("utf-8", errors="replace").decode("utf-8"), frame


def _render(
    data: bytes, max_pages: int, dpi: int, max_side: float
) -> list[tuple[Image.Image, str, _Frame]]:
    """Image (RGB), stream text and frame of each page, through PDFium. Raises `TooManyPages`,
    `PageTooLarge`, `RotatedPage`, or an error (protected, damaged, not a PDF)."""
    document = pdfium.PdfDocument(data)
    try:
        count = len(document)
        if count > max_pages:
            raise TooManyPages()
        if count == 0:
            raise ValueError("no page")
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
    """Layout of the PDF's pages (at most `max_pages`, `MAX_LAYOUT_BLOCKS` blocks in all), as a
    JSON-ready dictionary: `pages` (`width`, `height` of the CropBox, `blocks` as lists
    `[text, x0, top, x1, bottom, font, size, colour, bold, invisible]`, `png` in base64,
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
