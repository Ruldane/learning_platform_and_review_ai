"""Faux `FontSource` des tests (D119) : un petit fichier `.ttf` factice par famille du catalogue,
aucun réseau ; `unavailable` simule une famille introuvable, `calls` garde chaque demande."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.providers.fonts.base import DEFAULT_WEIGHTS, FontFile, FontUnavailable
from app.providers.fonts.catalog import FREE_FAMILIES


def fake_font_data(family: str, weight: int) -> bytes:
    """Octets reconnaissables : signature TrueType, puis la famille et la graisse."""
    return b"\x00\x01\x00\x00" + f"{family}:{weight}".encode()


@dataclass
class FakeFontSource:
    unavailable: set[str] = field(default_factory=set)
    calls: list[tuple[str, tuple[int, ...]]] = field(default_factory=list)

    async def fetch(self, family: str, weights: Sequence[int] = DEFAULT_WEIGHTS) -> list[FontFile]:
        self.calls.append((family, tuple(weights)))
        if family not in FREE_FAMILIES or family in self.unavailable:
            raise FontUnavailable()
        return [
            FontFile(family, weight, "normal", fake_font_data(family, weight), ".ttf")
            for weight in sorted(set(weights))
        ]
