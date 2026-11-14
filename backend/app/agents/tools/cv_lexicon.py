"""Lexique du CV partagé par les contrôles d'honnêteté (preflight G19) : la forme canonique des
nombres, écrite une seule fois. Le profil maître (`profile_check`, 6.8) et le validateur des
modifications (6.12) comparent ainsi « 30 % » et « 30% », « 1 000 » et « 1000 », « 12 k€ » et
« 12 000 € » sans se tromper de format. Le validateur des modifications (6.12) y ajoute les chiffres
écrits en lettres, les proportions (« moitié », « tiers », « x2 ») et les mots de titre."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.agents.tools.cv_tech_terms import TECH_TERMS as TECH_TERMS  # noqa: PLC0414
from app.agents.tools.posting_schema import normalize_term

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


# Chiffres écrits en lettres (sans accent) → forme canonique. « un », « une » et « one » manquent
# exprès (article) ; les ordres de grandeur vagues (« dizaines ») sont des figures à part entière :
# les inventer revient à inventer un chiffre.
NUMBER_WORDS: dict[str, str] = {
    **{w: str(n) for n, w in enumerate("deux trois quatre cinq six sept huit neuf dix".split(), 2)},  # noqa: SIM905
    **{w: str(n) for n, w in enumerate("two three four five six seven eight nine ten".split(), 2)},  # noqa: SIM905
    **{w: str(n) for n, w in enumerate("onze douze treize quatorze quinze seize".split(), 11)},  # noqa: SIM905
    "eleven": "11", "twelve": "12", "vingt": "20", "twenty": "20", "trente": "30",
    "thirty": "30", "quarante": "40", "forty": "40", "cinquante": "50", "fifty": "50",
    "soixante": "60", "sixty": "60", "cent": "100", "cents": "100", "hundred": "100",
    "mille": "1000", "thousand": "1000", "million": "1000000", "millions": "1000000",
    "milliard": "1000000000", "billion": "1000000000", "dizaine": "dizaines",
    "dizaines": "dizaines", "douzaine": "dizaines", "centaine": "centaines",
    "centaines": "centaines", "millier": "milliers", "milliers": "milliers",
}  # fmt: skip

# Mots de proportion → famille (« moitié » → « half »). Un mot de proportion exige un chiffre de
# la même famille (`RATIO_NUMBERS`) ou le même mot dans les faits cités.
RATIO_WORDS: dict[str, str] = {
    "moitié": "half", "moitie": "half", "half": "half", "tiers": "third", "quart": "quarter",
    "double": "double", "doubler": "double", "doublé": "double", "doublement": "double",
    "x2": "double", "triple": "triple", "tripler": "triple", "triplé": "triple", "x3": "triple",
    "quadruple": "quadruple", "quadrupler": "quadruple", "x4": "quadruple",
}  # fmt: skip
RATIO_NUMBERS: dict[str, frozenset[str]] = {
    "half": frozenset({"50%"}),
    "third": frozenset({"33%"}),
    "quarter": frozenset({"25%"}),
    "double": frozenset({"100%", "200%"}),
    "triple": frozenset({"200%", "300%"}),
    "quadruple": frozenset({"300%", "400%"}),
}

# Mots d'intitulé de poste : un titre absent du profil se « confirme ».
TITLE_WORDS: frozenset[str] = frozenset(
    """lead senior principal head manager directeur directrice chef cheffe responsable vp cto ceo
    cio coo architecte architect fondateur fondatrice founder président presidente gérant
    gérante
    """.split()  # noqa: SIM905
)

_ZERO_WIDTH = {"Cf"}  # caractères de format : espace de largeur nulle, marque directionnelle…
_PERCENT_WORDS = re.compile(r"(\d)\s*(?:pour\s*cent|per\s*cent|percent|pourcents?)", re.IGNORECASE)
_MULTIPLIER = re.compile(r"(?<!\w)(?:[x×]\s?(\d+)|(\d+)\s?[x×])(?!\w)", re.IGNORECASE)
_PERCENT_NEXT = (["pour", "cent"], ["per", "cent"])


def clean_text(text: str) -> str:
    """Le texte en forme NFKC (chiffres pleine chasse, espaces insécables, « ％ ») sans caractère
    de format invisible, et « 30 pour cent » écrit « 30% »."""
    plain = unicodedata.normalize("NFKC", text)
    plain = "".join(ch for ch in plain if unicodedata.category(ch) not in _ZERO_WIDTH)
    return _PERCENT_WORDS.sub(r"\1%", plain)


def figures_in(text: str) -> set[str]:
    """Les nombres de `text` (`numbers_in`) et ceux écrits en lettres (« trente pour cent » →
    « 30% », « dizaines »), sous forme canonique."""
    clean = clean_text(text)
    found = numbers_in(clean)
    tokens = normalize_term(clean).split()
    for rank, token in enumerate(tokens):
        figure = NUMBER_WORDS.get(token)
        if figure is None or (token == "cent" and rank and tokens[rank - 1] in ("pour", "per")):
            continue
        after = tokens[rank + 1 : rank + 3]
        found.add(f"{figure}%" if after in _PERCENT_NEXT or after[:1] == ["percent"] else figure)
    return found


def ratio_families(text: str) -> set[str]:
    """Les familles de proportion de `text` : « moitié », « un tiers », « doublé », « x2 »."""
    clean = clean_text(text)
    words = {normalize_term(word): family for word, family in RATIO_WORDS.items()}
    found = {words[token] for token in normalize_term(clean).split() if token in words}
    for match in _MULTIPLIER.finditer(clean):
        times = int(match.group(1) or match.group(2))
        found.add({2: "double", 3: "triple", 4: "quadruple"}.get(times, f"x{times}"))
    return found
