"""Catalogue of free fonts (OFL or Apache 2.0, all served by Google Fonts) and substitution table
for a font read from a PDF (D119). The name read from the PDF is never logged nor sent to a
service: only the catalogue family is."""

import re
from dataclasses import dataclass

FREE_FAMILIES: frozenset[str] = frozenset(
    {
        "Lato",
        "Roboto",
        "Open Sans",
        "Source Sans 3",
        "Montserrat",
        "Raleway",
        "Poppins",
        "Inter",
        "Merriweather",
        "Lora",
        "PT Sans",
        "PT Serif",
        "Noto Sans",
        "Noto Serif",
        "Nunito",
        "Work Sans",
        "IBM Plex Sans",
        "Fira Sans",
        "Carlito",
        "Caladea",
        "Liberation Sans",
        "Liberation Serif",
        "EB Garamond",
        "Gelasio",
        "Roboto Slab",
        "Playfair Display",
    }
)
DEFAULT_SANS = "Liberation Sans"
DEFAULT_SERIF = "Liberation Serif"
# Serif families of the catalogue (CSS fallback `serif`; the others: `sans-serif`).
SERIF_FAMILIES: frozenset[str] = frozenset(
    {
        "Merriweather",
        "Lora",
        "PT Serif",
        "Noto Serif",
        "Caladea",
        "Liberation Serif",
        "EB Garamond",
        "Gelasio",
        "Roboto Slab",
        "Playfair Display",
    }
)

# Proprietary font (start of the cleaned name, lowercase, no spaces) → close free family;
# the metrics are compatible for Arial, Helvetica, Times, Calibri and Cambria.
SUBSTITUTES: dict[str, str] = {
    "arial": "Liberation Sans",
    "helvetica": "Liberation Sans",
    "calibri": "Carlito",
    "cambria": "Caladea",
    "times": "Liberation Serif",
    "georgia": "Gelasio",
    "garamond": "EB Garamond",
    "segoe": "Noto Sans",
    "verdana": "Noto Sans",
    "tahoma": "Noto Sans",
    "aptos": "Noto Sans",
    "trebuchet": "Fira Sans",
    "gillsans": "Lato",
    "futura": "Montserrat",
    "centurygothic": "Montserrat",
    "avenir": "Nunito",
    "sourcesanspro": "Source Sans 3",
    "bookantiqua": "EB Garamond",
    "palatino": "EB Garamond",
}

_SUBSET = re.compile(r"^[A-Z]{6}\+")
# Style after a dash or a comma: « Lato-Bold », « Arial,Bold ».
_STYLE = re.compile(r"[-,].*$")
# Foundry suffixes: « ArialMT », « TimesNewRomanPSMT ».
_VENDOR = re.compile(r"(MT|PS)$")


@dataclass(frozen=True)
class FontChoice:
    """`original`: cleaned name read from the PDF (CV data, never logged); `family`: the catalogue
    family; `free`: the original font is itself free."""

    original: str
    family: str
    free: bool


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


_FREE_BY_KEY = {_key(family): family for family in FREE_FAMILIES}


def clean_name(pdf_font: str) -> str:
    """Without a subset prefix, without style, without a foundry suffix (repeated)."""
    name = _STYLE.sub("", _SUBSET.sub("", pdf_font.strip()))
    previous = None
    while previous != name:
        previous, name = name, _VENDOR.sub("", name)
    return name.strip()


def choose_font(pdf_font: str) -> FontChoice:
    """Free → itself; known → its substitute; otherwise « Liberation Serif » if the name suggests a
    serif font (serif, times, roman, without "sans"), « Liberation Sans » otherwise."""
    original = clean_name(pdf_font)
    key = _key(original)
    if key in _FREE_BY_KEY:
        return FontChoice(original, _FREE_BY_KEY[key], free=True)
    for prefix, family in SUBSTITUTES.items():
        if key.startswith(prefix):
            return FontChoice(original, family, free=False)
    serif = "sans" not in key and any(word in key for word in ("serif", "times", "roman"))
    return FontChoice(original, DEFAULT_SERIF if serif else DEFAULT_SANS, free=False)
