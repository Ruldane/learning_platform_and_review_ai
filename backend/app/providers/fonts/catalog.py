"""Catalogue des polices libres (OFL ou Apache 2.0, toutes servies par Google Fonts) et table de
substitution d'une police lue dans un PDF (D119). Le nom lu dans le PDF n'est jamais journalisé
ni envoyé à un service : seule la famille du catalogue l'est."""

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
# Familles du catalogue à empattement (repli CSS `serif` ; les autres : `sans-serif`).
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

# Police propriétaire (début du nom nettoyé, en minuscules sans espace) → famille libre proche ;
# les métriques sont compatibles pour Arial, Helvetica, Times, Calibri et Cambria.
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
# Style après un tiret ou une virgule : « Lato-Bold », « Arial,Bold ».
_STYLE = re.compile(r"[-,].*$")
# Suffixes de fonderie : « ArialMT », « TimesNewRomanPSMT ».
_VENDOR = re.compile(r"(MT|PS)$")


@dataclass(frozen=True)
class FontChoice:
    """`original` : nom nettoyé lu dans le PDF (donnée du CV, jamais journalisée) ; `family` :
    famille du catalogue ; `free` : la police d'origine est elle-même libre."""

    original: str
    family: str
    free: bool


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


_FREE_BY_KEY = {_key(family): family for family in FREE_FAMILIES}


def clean_name(pdf_font: str) -> str:
    """Sans préfixe de sous-ensemble, sans style, sans suffixe de fonderie (répété)."""
    name = _STYLE.sub("", _SUBSET.sub("", pdf_font.strip()))
    previous = None
    while previous != name:
        previous, name = name, _VENDOR.sub("", name)
    return name.strip()


def choose_font(pdf_font: str) -> FontChoice:
    """Libre → elle-même ; connue → son substitut ; sinon « Liberation Serif » si le nom évoque
    une police à empattement (serif, times, roman, sans « sans »), « Liberation Sans » sinon."""
    original = clean_name(pdf_font)
    key = _key(original)
    if key in _FREE_BY_KEY:
        return FontChoice(original, _FREE_BY_KEY[key], free=True)
    for prefix, family in SUBSTITUTES.items():
        if key.startswith(prefix):
            return FontChoice(original, family, free=False)
    serif = "sans" not in key and any(word in key for word in ("serif", "times", "roman"))
    return FontChoice(original, DEFAULT_SERIF if serif else DEFAULT_SANS, free=False)
