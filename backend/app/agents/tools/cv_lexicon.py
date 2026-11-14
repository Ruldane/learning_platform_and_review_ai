"""Lexique du CV partagé par les contrôles d'honnêteté (preflight G19) : la forme canonique des
nombres, écrite une seule fois. Le profil maître (`profile_check`, 6.8) et le validateur des
modifications (6.12) comparent ainsi « 30 % » et « 30% », « 1 000 » et « 1000 », « 12 k€ » et
« 12 000 € » sans se tromper de format."""

import re
from decimal import Decimal, InvalidOperation

# Un nombre : groupes de milliers séparés par une espace (normale, insécable, fine insécable) ou
# chiffres collés ; partie décimale à la virgule ou au point ; multiplicateur « k » ou « M »
# (pas « Mo », « km ») ; signe « % » éventuel. Jamais au milieu d'un mot ni d'un autre nombre.
_NUMBER = re.compile(
    r"(?<![\w.,])"
    r"(?P<int>\d{1,3}(?:[   ]\d{3})+(?!\d)|\d+)"
    r"(?:[.,](?P<dec>\d+))?"
    r"(?:[   ]?(?P<mult>[kKM])(?![A-Za-zÀ-ÿ]))?"
    r"(?P<pct>[   ]?%)?"
)
_SEPARATORS = re.compile(r"[   ]")
_MULTIPLIERS = {"k": Decimal(1000), "K": Decimal(1000), "M": Decimal(1_000_000)}


def _canonical(match: re.Match[str]) -> str | None:
    digits = _SEPARATORS.sub("", match.group("int"))
    decimals = match.group("dec")
    try:
        value = Decimal(f"{digits}.{decimals}" if decimals else digits)
    except InvalidOperation:
        return None
    if mult := match.group("mult"):
        value *= _MULTIPLIERS[mult]
    text = format(value.normalize(), "f")
    return f"{text}%" if match.group("pct") else text


def numbers_in(text: str) -> set[str]:
    """Les nombres de `text`, sous forme canonique : « 30 % » → « 30% », « 1 000 » et « 1000 »
    → « 1000 », « 12 k€ » → « 12000 », « 2,50 » → « 2.5 ». Un pourcentage reste distinct du
    nombre nu (« 30 % » n'est pas « 30 personnes »)."""
    found: set[str] = set()
    for match in _NUMBER.finditer(text):
        canonical = _canonical(match)
        if canonical is not None:
            found.add(canonical)
    return found
