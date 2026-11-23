"""Rattache les chiffres et proportions d'une proposition aux mesures citées par le profil."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.agents.tools.cv_lexicon import (
    RATIO_NUMBERS,
    RATIO_WORDS,
    clean_text,
    figure_spans,
    ratio_families,
)
from app.agents.tools.posting_schema import normalize_term

_BREAK = re.compile(r"(\b(?:et|and)\b|[;!?\n]|[.,]\s+(?!(?:soit|ou|or)\b))", re.IGNORECASE)
_STOP_WORDS = set(
    """au aux avec ce ces dans de des du en la le les leur par pour sur un une
    an and by for from in of on or the to with gagne gagnee gagnees enleve moins plus
    soit a d l s x ni environ approximativement about approximately""".split()  # noqa: SIM905
)
_PROPORTIONS = {normalize_term(word) for word in RATIO_WORDS}
_DOWN = re.compile(r"reduc\w*|redui\w*|reduit\w*|baiss\w*|raccourci\w*|dimin\w*|lower\w*|cut")
_UP = re.compile(r"augment\w*|hausse\w*|increas\w*|rais\w*|grow\w*")
_SIGN = re.compile(r"(?<!\w)([+−-])\s*$")
_CURRENCIES = frozenset("€$£")
_UNITS = {
    "h", "heure", "hour", "minute", "min", "seconde", "second",
    "jour", "day", "semaine", "week", "moi", "month", "an", "annee", "year",
}  # fmt: skip
_ORDERED_ROLES = {
    ("de", "a"): "transition",
    ("from", "to"): "transition",
    ("entre", "et"): "range",
    ("between", "and"): "range",
}
_TRANSITION_WORDS = {"passage", "passe", "passer", "transition"}


@dataclass(frozen=True)
class _Measure:
    signature: tuple[str, ...]
    figures: tuple[str, ...]
    ratios: frozenset[str]
    anchors: frozenset[str]
    units: frozenset[str]
    currencies: frozenset[str]
    direction: str
    ordered_role: str


def _ordered_role(text: str, spans: list[tuple[int, int, str]]) -> str:
    if len(spans) != 2:
        return ""
    (first, end, _), (second, _, _) = spans
    before = normalize_term(text[:first]).split()
    connector = normalize_term(text[end:second])
    return _ORDERED_ROLES.get((before[-1], connector), "") if before else ""


def _measure(text: str, inherited_direction: str) -> _Measure:
    spans = figure_spans(text)
    words, signature = [], []
    signs: set[str] = set()
    currencies: set[str] = set()
    start = 0
    for left, right, figure in spans:
        before = text[start:left]
        sign = match.group(1).replace("−", "-") if (match := _SIGN.search(before)) else ""
        currency = "".join(ch for ch in text[left:right] if ch in _CURRENCIES)
        if not currency and (prefix := before.rstrip()) and prefix[-1] in _CURRENCIES:
            currency = prefix[-1]
        signs.add(sign)
        currencies.update(currency)
        words.extend(normalize_term(before, plural=True).split())
        signature.extend([*normalize_term(before).split(), f"#{sign}{figure}{currency}"])
        start = right
    words.extend(normalize_term(text[start:], plural=True).split())
    signature.extend(normalize_term(text[start:]).split())
    terms = set(words).difference(_STOP_WORDS, _PROPORTIONS)
    down = {word for word in terms if _DOWN.fullmatch(word)}
    up = {word for word in terms if _UP.fullmatch(word)}
    normalized = f" {normalize_term(text)} "
    falling = bool(down) or "-" in signs or " en moins " in normalized
    rising = bool(up) or "+" in signs or " en plus " in normalized
    direction = "mixed" if falling and rising else "down" if falling else "up" if rising else ""
    ordered_role = _ordered_role(text, spans)
    if ordered_role == "transition":
        terms.difference_update(_TRANSITION_WORDS)
    units = terms & _UNITS
    anchors = {word for word in terms - down - up - units if len(word) > 1 and not word.isdigit()}
    return _Measure(
        tuple(signature),
        tuple(figure for _, _, figure in spans),
        frozenset(ratio_families(text)),
        frozenset(anchors),
        frozenset(units),
        frozenset(currencies),
        direction or inherited_direction,
        ordered_role,
    )


def _clauses(clean: str) -> Iterable[str]:
    parts = _BREAK.split(clean)
    clause = parts[0]
    for separator, following in zip(parts[1::2], parts[2::2], strict=True):
        if separator.casefold() in ("et", "and"):
            joined = f"{clause}{separator}{following}"
            if _ordered_role(joined, figure_spans(joined)) == "range":
                clause = joined
                continue
        yield clause
        clause = following
    yield clause


def _measures(text: str) -> list[_Measure]:
    measures: list[_Measure] = []
    pending = ""
    for part in _clauses(clean_text(text)):
        pending = f"{pending} {part}"
        measure = _measure(pending, measures[-1].direction if measures else "")
        if measure.figures or measure.ratios:
            measures.append(measure)
            pending = ""
    return measures


def _amount_matches(claim: _Measure, source: _Measure) -> bool:
    if len(claim.figures) > 1 or len(source.figures) > 1:
        return (
            bool(claim.ordered_role)
            and claim.ordered_role == source.ordered_role
            and claim.figures == source.figures
            and claim.ratios == source.ratios
        )
    return set(claim.figures) <= set(source.figures) and all(
        ratio in source.ratios or bool(RATIO_NUMBERS.get(ratio, frozenset()) & set(source.figures))
        for ratio in claim.ratios
    )


def _measure_matches(claim: _Measure, source: _Measure, references: list[_Measure]) -> bool:
    if claim.direction and source.direction and claim.direction != source.direction:
        return False
    if claim.signature == source.signature:
        return True
    if not _amount_matches(claim, source):
        return False
    if "mixed" in (claim.direction, source.direction):
        return False
    if claim.currencies and source.currencies and claim.currencies != source.currencies:
        return False
    if claim.units and source.units and not claim.units & source.units:
        return False
    if not claim.anchors or not source.anchors:
        return bool(claim.units & source.units)
    shared = claim.anchors & source.anchors
    if not shared or (claim.anchors - shared and source.anchors - shared):
        return False
    return not any(
        (claim.anchors - shared) & other.anchors and not _amount_matches(claim, other)
        for other in references
    )


def numeric_claims_supported(after: str, facts: Iterable[str]) -> bool:
    """Chaque mesure chiffrée doit conserver le montant d'une mesure citée identifiable."""
    claims = _measures(after)
    if not claims:
        return True
    sources = [measure for fact in facts for measure in _measures(fact)]
    return all(
        any(_measure_matches(claim, source, sources) for source in sources) for claim in claims
    )
