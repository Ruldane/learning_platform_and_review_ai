"""Free fonts port (D119): the files of a catalogue family (`catalog.py`), attached to the
rendering of a CV template. Only catalogue families are requested: never a font name
read from a PDF."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.errors import AppError

DEFAULT_WEIGHTS = (400, 700)
FONT_TIMEOUT_S = 15.0
FONT_MAX_BYTES = 2 * 1024 * 1024


class FontUnavailable(AppError):
    """Font not found or service unreachable (timeout, refusal, file too large or invalid). The
    message quotes neither the address nor the response."""

    def __init__(self) -> None:
        super().__init__("font_unavailable", "Font unavailable for the moment.", status_code=502)


@dataclass(frozen=True)
class FontFile:
    family: str
    weight: int
    style: Literal["normal", "italic"]
    data: bytes
    suffix: Literal[".woff2", ".ttf"]

    @property
    def asset_name(self) -> str:
        """Resource name accepted by `HtmlDocument`: "source-sans-3-400.ttf",
        "lato-700-italic.woff2"."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.family.lower()).strip("-") or "font"
        italic = "-italic" if self.style == "italic" else ""
        return f"{slug}-{self.weight}{italic}{self.suffix}"


class FontSource(Protocol):
    async def fetch(self, family: str, weights: Sequence[int] = DEFAULT_WEIGHTS) -> list[FontFile]:
        """Files of `family` (a catalogue family) at the requested weights, normal style;
        `FontUnavailable` otherwise."""
        ...
