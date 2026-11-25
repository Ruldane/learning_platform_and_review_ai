"""Fake `FontSource` for tests (D119): a small fake `.ttf` file per catalogue family, no network;
`unavailable` simulates a family not found, `calls` keeps each request."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.providers.fonts.base import DEFAULT_WEIGHTS, FontFile, FontUnavailable
from app.providers.fonts.catalog import FREE_FAMILIES


def fake_font_data(family: str, weight: int) -> bytes:
    """Recognizable bytes: TrueType signature, then the family and the weight."""
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
