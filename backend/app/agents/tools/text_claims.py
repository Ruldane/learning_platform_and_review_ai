"""Contrôle des faits d'un texte écrit au nom de January (SPEC 1, 18.3, F16) : pièces du kit de
candidature, brouillons de relance, pitch, réponses de formulaire, réponse améliorée du débrief.
Du code, pas un agent : un chiffre, un outil, un titre ou un nom propre que le profil maître validé
ne dit pas est rendu (`Claim`), et la pièce reste « à vérifier » avec ces termes.

Mêmes lectures que le validateur des modifications de CV (`cv_validator`, `cv_lexicon`) : nombres
(chiffres et lettres, « 30 % », « 12 k€ »), outils du lexique (un terme ambigu comme « vue » ou
« spring » seulement sous sa forme de produit), mots de titre (« lead », « senior »…), mots
capitalisés hors début de phrase. La référence est tout le profil (faits, dates, compétences,
langues, liens, identité) ; `allowed` y ajoute ce que le texte peut citer comme étant de l'offre ou
de l'entreprise (« votre poste de Développeuse IA ») : jamais les chiffres de l'offre (« 3 ans
requis »), qui ne sont pas des faits de January. Les phrases doivent parler de January."""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.agents.tools.cv_lexicon import (
    AMBIGUOUS_TERMS,
    NUMBER_WORDS,
    TECH_TERMS,
    TITLE_WORDS,
    clean_text,
    figures_in,
    number_spans,
)
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.cv_validator import capitalized_names, product_forms
from app.agents.tools.posting_schema import normalize_term

ClaimKind = Literal["number", "tool", "title", "name"]
_WORD = re.compile(r"\w[\w+#]*")
_SKIPPED_KEYS = frozenset({"id", "sources"})  # identifiants et origines : pas du texte de January
# Formules d'adresse et dates anglaises : capitalisées sans être des noms propres du profil.
_COURTESY = [
    "madame",
    "monsieur",
    "mademoiselle",
    "messieurs",
    "mesdames",
    "dear",
    "sir",
    "madam",
    "hello",
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def _tech_by_first_word() -> dict[str, list[tuple[str, tuple[str, ...]]]]:
    """Les outils du lexique, comparés (`normalize_term`), rangés par leur premier mot."""
    index: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for term in TECH_TERMS:
        form = normalize_term(term, plural=True)
        index.setdefault(form.split()[0], []).append((form, tuple(form.split())))
    return index


_TECH_BY_FIRST = _tech_by_first_word()
_AMBIGUOUS = {normalize_term(term, plural=True) for term in AMBIGUOUS_TERMS}
_TITLES = {normalize_term(word, plural=True) for word in TITLE_WORDS}


@dataclass(frozen=True)
class Claim:
    """Un terme du texte que le profil ne dit pas, tel que le texte l'écrit (un nombre sous sa
    forme canonique : « 30% », « 1000 »)."""

    kind: ClaimKind
    term: str


Found = dict[tuple[ClaimKind, str], tuple[int, Claim]]  # (genre, clé) → (position, claim)


def _strings(value: Any) -> Iterator[str]:
    """Les textes d'un profil (`model_dump`), sans identifiants ni origines."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in _SKIPPED_KEYS:
                yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _padded(text: str) -> str:
    return f" {normalize_term(text, plural=True)} "


def _words(text: str) -> list[tuple[str, int, int]]:
    """Les mots de `text` comparables (`normalize_term`) : `(mot, début, fin)` dans le texte."""
    return [
        (part, match.start(), match.end())
        for match in _WORD.finditer(text)
        for part in normalize_term(match.group(), plural=True).split()
    ]


def _number_claims(text: str, reference: str) -> Found:
    unbacked = figures_in(text) - figures_in(reference)
    found: Found = {}
    for position, figure in number_spans(text):
        if figure in unbacked:
            found.setdefault(("number", figure), (position, Claim("number", figure)))
    previous = ""
    for match in _WORD.finditer(text):
        word = normalize_term(match.group())
        spelled = NUMBER_WORDS.get(word)
        if spelled is not None and not (word == "cent" and previous in ("pour", "per")):
            percent = f"{spelled}%"
            key = percent if percent in unbacked and spelled not in unbacked else spelled
            if key in unbacked:
                found.setdefault(("number", key), (match.start(), Claim("number", match.group())))
        previous = word
    return found


def _tool_claims(text: str, known: str) -> Found:
    product = product_forms(text)
    words = _words(text)
    found: Found = {}
    for rank, (word, start, _) in enumerate(words):
        for form, parts in _TECH_BY_FIRST.get(word, ()):
            window = words[rank : rank + len(parts)]
            if tuple(part for part, _, _ in window) != parts or f" {form} " in known:
                continue
            if form in _AMBIGUOUS and form not in product:
                continue
            claim = Claim("tool", text[start : window[-1][2]])
            found.setdefault(("tool", form), (start, claim))
    return found


def _title_claims(text: str, known_titles: str) -> Found:
    found: Found = {}
    for match in _WORD.finditer(text):
        form = normalize_term(match.group(), plural=True)
        if form in _TITLES and f" {form} " not in known_titles:
            found.setdefault(("title", form), (match.start(), Claim("title", match.group())))
    return found


def _name_claims(text: str, known: str, taken: set[str]) -> Found:
    """Les noms propres inconnus, sauf ceux déjà rendus comme outil ou comme titre."""
    found: Found = {}
    for position, word in capitalized_names(text, known, skip_first=True):
        form = normalize_term(word, plural=True)
        if form not in taken:
            found[("name", form)] = (position, Claim("name", word))
    return found


def _title_texts(profile: MasterProfileData, allowed: Sequence[str]) -> str:
    texts = [experience.role for experience in profile.experiences]
    texts += [line.text for line in (profile.title,) if line is not None]
    return _padded(" ".join([*texts, profile.identity.headline or "", *allowed]))


def text_claims(
    text: str, profile: MasterProfileData, *, allowed: Sequence[str] = ()
) -> list[Claim]:
    """Les chiffres, outils, titres et noms propres de `text` que le profil ne dit pas, sans
    doublon, dans l'ordre du texte. `allowed` : l'entreprise, l'intitulé et les mots de l'offre
    que le texte cite comme tels (jamais un chiffre de l'offre)."""
    clean = clean_text(text)
    reference = clean_text(" ".join([*_strings(profile.model_dump()), *allowed]))
    known = _padded(f"{reference} {' '.join(_COURTESY)}")
    found = {**_number_claims(clean, reference), **_tool_claims(clean, known)}
    found |= _title_claims(clean, _title_texts(profile, allowed))
    taken = {form for _, form in found}
    taken |= {tok for _, form in found for tok in form.split()}
    found |= _name_claims(clean, known, taken)
    return [claim for _, claim in sorted(found.values(), key=lambda item: item[0])]
