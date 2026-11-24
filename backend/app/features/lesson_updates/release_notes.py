"""Collects the API replacements explicitly named in the changelog."""

import re
from dataclasses import dataclass

_SYMBOL = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"
_VERSION = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.\d+)?)(?![\w.]|[-+]\w)", re.I)
_REPLACED = (
    re.compile(
        rf"(?:removed|deprecated|supprim\w+|obsolète)\s+`?({_SYMBOL})`?\s*[;,.–—:]\s*"
        rf"(?:use|utilise[rz]?)\s+`?({_SYMBOL})`?",
        re.I,
    ),
    re.compile(
        rf"`?({_SYMBOL})`?\s+(?:(?:was|est)\s+)?(?:renamed to|replaced (?:by|with)|"
        rf"remplac\w+ par|renomm\w+ en)\s+`?({_SYMBOL})`?",
        re.I,
    ),
)


@dataclass(frozen=True)
class ApiChange:
    previous: str
    replacement: str
    evidence: str


@dataclass(frozen=True)
class Release:
    library: str
    version: str
    url: str
    changes: tuple[ApiChange, ...]


def changes_in(title: str, text: str, url: str) -> list[Release]:
    version = _VERSION.search(title) or _VERSION.search(url)
    if version is None:
        return []
    by_library: dict[str, dict[str, ApiChange]] = {}
    for raw in text[:16_000].splitlines():
        line = raw.strip()
        if len(line) > 450:
            continue
        for pattern in _REPLACED:
            for match in pattern.finditer(line):
                previous, replacement = match.groups()
                library = previous.split(".")[0]
                if previous == replacement or replacement.split(".")[0] != library:
                    continue
                found = by_library.setdefault(library, {})
                if len(found) < 12:
                    found.setdefault(previous, ApiChange(previous, replacement, line))
    return [
        Release(library, version[1], url, tuple(changes.values()))
        for library, changes in by_library.items()
    ]
