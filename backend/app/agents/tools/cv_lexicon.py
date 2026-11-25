"""CV lexicon shared by the honesty checks (preflight G19): the canonical form of numbers,
written once. The master profile (`profile_check`, 6.8) and the change validator (6.12) thus
compare "30 %" and "30%", "1 000" and "1000", "12 k€" and "12 000 €" without mixing up formats.
The change validator (6.12) adds to it the figures written in words, the proportions
("moitié", "tiers", "x2") and the title words. The French entries stay next to the English
ones: profiles, CVs and postings stored before the switch are French."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.agents.tools.cv_tech_terms import AMBIGUOUS_TERMS as AMBIGUOUS_TERMS  # noqa: PLC0414
from app.agents.tools.cv_tech_terms import TECH_TERMS as TECH_TERMS  # noqa: PLC0414
from app.agents.tools.posting_schema import normalize_term

# A number: thousands groups separated by a space (normal, no-break, narrow no-break), by a
# dot or a comma ("1,000" and "1.000": exactly three digits, first group without a leading
# zero: "0,125" stays decimal) or digits stuck together; decimal part with a comma or a
# dot; multiplier "k" or "M" (not "Mo", "km"); currency; optional "%" sign. Never in the
# middle of a word or of another number. A single group "1,500" followed by a multiplier or
# a currency ("1,500 M€") is a French decimal (1.5), see `_FRENCH_DECIMAL`.
_NUMBER = re.compile(
    r"(?<![\w.,])"
    r"(?P<int>\d{1,3}(?:[   ]\d{3})+(?!\d)|[1-9]\d{0,2}(?:[.,]\d{3})+(?!\d)|\d+)"
    r"(?:[.,](?P<dec>\d+))?"
    r"(?:[   ]?(?P<mult>[kKM])(?![A-Za-zÀ-ÿ]))?"
    r"(?P<cur>[   ]?[€$£])?"
    r"(?P<pct>[   ]?%)?"
)
_SEPARATORS = re.compile(r"[   .,]")  # spaces and dots or commas of thousands
# "1,500": a single thousands group, with a comma
_FRENCH_DECIMAL = re.compile(r"[1-9]\d{0,2},\d{3}")
_MULTIPLIERS = {"k": Decimal(1000), "K": Decimal(1000), "M": Decimal(1_000_000)}


def _canonical(match: re.Match[str]) -> str | None:
    whole, decimals = match.group("int"), match.group("dec")
    unit = match.group("mult") or match.group("cur")
    if unit and not decimals and _FRENCH_DECIMAL.fullmatch(whole):
        whole = whole.replace(",", ".")  # "1,500 M€": one and a half million, not 1 500 M
        digits, decimals = whole.split(".")
    else:
        digits = _SEPARATORS.sub("", whole)
    try:
        value = Decimal(f"{digits}.{decimals}" if decimals else digits)
    except InvalidOperation:
        return None
    if mult := match.group("mult"):
        value *= _MULTIPLIERS[mult]
    text = format(value.normalize(), "f")
    return f"{text}%" if match.group("pct") else text


def number_spans(text: str) -> list[tuple[int, str]]:
    """The numbers of `text`, in text order: `(position, canonical form)`."""
    spans: list[tuple[int, str]] = []
    for match in _NUMBER.finditer(text):
        canonical = _canonical(match)
        if canonical is not None:
            spans.append((match.start(), canonical))
    return spans


def numbers_in(text: str) -> set[str]:
    """The numbers of `text`, in canonical form: "30 %" -> "30%", "1 000" and "1000"
    -> "1000", "12 k€" -> "12000", "2,50" -> "2.5". A percentage stays distinct from the
    bare number ("30 %" is not "30 people")."""
    return {canonical for _, canonical in number_spans(text)}


# Numbers written in words (no accent) -> canonical form. "un", "une" and "one" are missing
# on purpose (article); vague orders of magnitude ("dizaines") are figures in their own right:
# inventing them amounts to inventing a figure.
NUMBER_WORDS: dict[str, str] = {
    **{w: str(n) for n, w in enumerate("deux trois quatre cinq six sept huit neuf dix".split(), 2)},  # noqa: SIM905
    **{w: str(n) for n, w in enumerate("two three four five six seven eight nine ten".split(), 2)},  # noqa: SIM905
    **{w: str(n) for n, w in enumerate("onze douze treize quatorze quinze seize".split(), 11)},  # noqa: SIM905
    "eleven": "11", "twelve": "12", "vingt": "20", "twenty": "20", "trente": "30",
    "thirty": "30", "quarante": "40", "forty": "40", "cinquante": "50", "fifty": "50",
    "soixante": "60", "sixty": "60", "cent": "100", "cents": "100", "hundred": "100",
    "mille": "1000", "thousand": "1000", "million": "1000000", "millions": "1000000",
    "milliard": "1000000000", "billion": "1000000000", "zero": "0", "dozen": "12",
    # Approximations: a word, an order of magnitude ("une trentaine" is not "32").
    **{w: "dizaines" for w in ("dizaine", "dizaines", "dozens")},
    **{w: "centaines" for w in ("centaine", "centaines", "hundreds")},
    **{w: "milliers" for w in ("millier", "milliers", "thousands")},
    **{
        w: w if w.endswith("s") else f"{w}s"
        for w in ("douzaine", "douzaines", "quinzaine", "quinzaines", "vingtaine", "vingtaines",
                  "trentaine", "trentaines", "quarantaine", "quarantaines", "cinquantaine",
                  "cinquantaines", "soixantaine", "soixantaines")
    },
}  # fmt: skip

# Proportion words -> family ("moitié" -> "half"). A proportion word requires a figure of the
# same family (`RATIO_NUMBERS`) or the same word in the cited facts.
RATIO_WORDS: dict[str, str] = {
    "moitié": "half", "moitie": "half", "half": "half", "tiers": "third", "quart": "quarter",
    "double": "double", "doubler": "double", "doublé": "double", "doublement": "double",
    "x2": "double", "triple": "triple", "tripler": "triple", "triplé": "triple", "x3": "triple",
    "quadruple": "quadruple", "quadrupler": "quadruple", "x4": "quadruple",
    "quadruplé": "quadruple", "doubled": "double", "doubles": "double", "twice": "double",
    "twofold": "double", "tripled": "triple", "thrice": "triple", "threefold": "triple",
    "quadrupled": "quadruple", "fourfold": "quadruple", "halved": "half", "halve": "half",
    "halving": "half", "tenfold": "x10", "décuplé": "x10", "décupler": "x10",
    "décuplement": "x10", "quintuplé": "x5", "quintuple": "x5", "quintupled": "x5",
    "fivefold": "x5",
}  # fmt: skip
# "divisé par deux": half; "par trois": a third; "par quatre": a quarter.
_RATIO_PHRASES = (
    (re.compile(r"divis\w* (?:par|by) (?:deux|2|two)(?!\d)|divided by (?:two|2)(?!\d)"), "half"),
    (re.compile(r"divis\w* par (?:trois|3)(?!\d)|divided by (?:three|3)(?!\d)"), "third"),
    (re.compile(r"divis\w* par (?:quatre|4)(?!\d)|divided by (?:four|4)(?!\d)"), "quarter"),
)
RATIO_NUMBERS: dict[str, frozenset[str]] = {
    "half": frozenset({"50%"}),
    "third": frozenset({"33%"}),
    "quarter": frozenset({"25%"}),
    "double": frozenset({"100%", "200%"}),
    "triple": frozenset({"200%", "300%"}),
    "quadruple": frozenset({"300%", "400%"}),
}

# Job title words: a title absent from the profile has to be "confirmed".
TITLE_WORDS: frozenset[str] = frozenset(
    """lead senior principal head manager directeur directrice chef cheffe responsable vp cto ceo
    cio coo architecte architect fondateur fondatrice founder président presidente gérant
    gérante director chief staff owner consultant consultante
    """.split()  # noqa: SIM905
)

_ZERO_WIDTH = {"Cf"}  # format characters: zero-width space, directional mark...
_PERCENT_WORDS = re.compile(r"(\d)\s*(?:pour\s*cent|per\s*cent|percent|pourcents?)", re.IGNORECASE)
_MULTIPLIER = re.compile(r"(?<!\w)(?:[x×]\s?(\d+)|(\d+)\s?[x×])(?!\w)", re.IGNORECASE)
_PERCENT_NEXT = (["pour", "cent"], ["per", "cent"])


def clean_text(text: str) -> str:
    """The text in NFKC form (full-width digits, no-break spaces, "％") without invisible
    format characters, and "30 pour cent" written "30%"."""
    plain = unicodedata.normalize("NFKC", text)
    plain = "".join(ch for ch in plain if unicodedata.category(ch) not in _ZERO_WIDTH)
    return _PERCENT_WORDS.sub(r"\1%", plain)


def figures_in(text: str) -> set[str]:
    """The numbers of `text` (`numbers_in`) and those written in words ("trente pour cent" ->
    "30%", "dizaines"), in canonical form."""
    return {value for _, _, value in figure_spans(clean_text(text))}


def figure_spans(clean: str) -> list[tuple[int, int, str]]:
    """Positions and canonical forms of the numbers in a text passed through `clean_text`."""
    found = [
        (match.start(), match.end(), value)
        for match in _NUMBER.finditer(clean)
        if (value := _canonical(match)) is not None
    ]
    words = list(re.finditer(r"(?:[^\W_]|[+#])+", clean))
    tokens = [normalize_term(word.group()) for word in words]
    for rank, (word, token) in enumerate(zip(words, tokens, strict=True)):
        figure = NUMBER_WORDS.get(token)
        if figure is None or (token == "cent" and rank and tokens[rank - 1] in ("pour", "per")):
            continue
        after = tokens[rank + 1 : rank + 3]
        percent_words = 2 if after in _PERCENT_NEXT else int(after[:1] == ["percent"])
        if percent_words:
            figure += "%"
        found.append((word.start(), words[rank + percent_words].end(), figure))
    return sorted(found)


def ratio_families(text: str) -> set[str]:
    """The proportion families of `text`: "moitié", "un tiers", "doublé", "x2"."""
    clean = clean_text(text)
    words = {normalize_term(word): family for word, family in RATIO_WORDS.items()}
    plain = normalize_term(clean)
    found = {words[token] for token in plain.split() if token in words}
    found |= {family for pattern, family in _RATIO_PHRASES if pattern.search(plain)}
    for match in _MULTIPLIER.finditer(clean):
        times = int(match.group(1) or match.group(2))
        found.add({2: "double", 3: "triple", 4: "quadruple"}.get(times, f"x{times}"))
    return found
