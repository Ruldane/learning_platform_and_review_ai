"""Port des polices libres (D119) : les fichiers d'une famille du catalogue (`catalog.py`), joints
au rendu d'un gabarit de CV. Seules des familles du catalogue sont demandées : jamais un nom de
police lu dans un PDF."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.errors import AppError

DEFAULT_WEIGHTS = (400, 700)
FONT_TIMEOUT_S = 15.0
FONT_MAX_BYTES = 2 * 1024 * 1024


class FontUnavailable(AppError):
    """Police introuvable ou service injoignable (délai, refus, fichier trop gros ou invalide). Le
    message ne cite ni l'adresse ni la réponse."""

    def __init__(self) -> None:
        super().__init__("font_unavailable", "Police indisponible pour le moment.", status_code=502)


@dataclass(frozen=True)
class FontFile:
    family: str
    weight: int
    style: Literal["normal", "italic"]
    data: bytes
    suffix: Literal[".woff2", ".ttf"]

    @property
    def asset_name(self) -> str:
        """Nom de ressource accepté par `HtmlDocument` : « source-sans-3-400.ttf »,
        « lato-700-italic.woff2 »."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.family.lower()).strip("-") or "police"
        italic = "-italic" if self.style == "italic" else ""
        return f"{slug}-{self.weight}{italic}{self.suffix}"


class FontSource(Protocol):
    async def fetch(self, family: str, weights: Sequence[int] = DEFAULT_WEIGHTS) -> list[FontFile]:
        """Fichiers de `family` (une famille du catalogue) aux graisses demandées, style normal ;
        `FontUnavailable` sinon."""
        ...
