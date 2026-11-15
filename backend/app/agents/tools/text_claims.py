"""Contrôle des faits d'un texte écrit au nom de January (SPEC 1, 18.3, F16) : pièces du kit de
candidature, brouillons de relance, pitch, réponses de formulaire, réponse améliorée du débrief.
Du code, pas un agent : un chiffre, un outil, un titre ou un nom propre que le profil maître validé
ne dit pas est rendu (`Claim`), et la pièce reste « à vérifier » avec ces termes. Mieux vaut
trop signaler (un humain lève) que laisser passer un fait inventé.

Lectures du validateur des modifications de CV (`cv_validator`, `cv_lexicon`) :
- **nombres** (chiffres et lettres, « 30 % », « 12 k€ ») et **proportions** (« doublé », « x3 »)
  absents des textes des faits du profil (titres, lignes, réalisations, résumé, détails de
  formation, compétences, langues) et des années de leurs dates de début et de fin. Jamais les
  chiffres d'un téléphone, d'un email ou d'un lien, ni les mois : ce ne sont pas des faits ;
- **outils** du lexique, sans casse (un terme ambigu comme « vue » seulement sous sa forme de
  produit), absents du profil ;
- **titres** (« lead », « senior »…) absents des intitulés du profil, seulement quand le texte se
  les attribue (« en tant que », « je suis », « comme », « as a »…) ;
- **noms propres** (`text_claims_names`).

`allowed` ne contient que des expressions entières : l'entreprise, l'intitulé exact de l'offre, le
nom d'un contact. Une expression est retirée du texte là où elle figure (`text_claims_mask`) :
partout pour les noms, et pour le reste seulement quand un mot de l'offre ou de l'employeur la
précède (« votre poste de Développeuse IA », « chez Société Fictive ») : « en tant que Lead Data »
reste lu. Les outils et les mots clés de l'offre n'y ont pas leur place, ni aucun chiffre : ils
ne sont jamais un fait de January. Les phrases doivent parler de January."""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.agents.tools.cv_lexicon import (
    AMBIGUOUS_TERMS,
    NUMBER_WORDS,
    RATIO_NUMBERS,
    RATIO_WORDS,
    TECH_TERMS,
    TITLE_WORDS,
    clean_text,
    figures_in,
    number_spans,
    ratio_families,
)
from app.agents.tools.cv_schema import Education, Experience, MasterProfileData, facts_of
from app.agents.tools.cv_validator import product_forms
from app.agents.tools.posting_schema import normalize_term
from app.agents.tools.text_claims_mask import (
    SELF_CUES,
    mask_dates,
    mask_own_contacts,
    mask_phrases,
)
from app.agents.tools.text_claims_names import GREETINGS, name_claims

ClaimKind = Literal["number", "tool", "title", "name"]
_WORD = re.compile(r"\w[\w+#]*")
_SKIPPED_KEYS = frozenset({"id", "sources"})  # identifiants et origines : pas du texte de January
_LINK_FACT = re.compile(r"^k\d+$")  # un lien : son adresse n'est pas une référence de chiffres
_CLAUSE_BREAK = re.compile(r"[.,;:!?\n]")
_TIMES = re.compile(r"(?<!\w)(?:[x×]\s?\d+|\d+\s?[x×])(?!\w)", re.IGNORECASE)
_SELF_WINDOW = 6  # mots après la formule où un mot de titre est lu


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
_RATIO_WORDS = {normalize_term(word): family for word, family in RATIO_WORDS.items()}


@dataclass(frozen=True)
class Claim:
    """Un terme du texte que le profil ne dit pas, tel que le texte l'écrit (un nombre sous sa
    forme canonique : « 30% », « 1000 » ; une proportion, le mot écrit : « doublé »)."""

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


def _fact_text(profile: MasterProfileData) -> str:
    """Les textes des faits (hors liens) et le titre d'en-tête : la référence des chiffres et des
    proportions. Les mois et les chiffres de contact n'y sont pas."""
    facts = [text for fact, text in facts_of(profile).items() if not _LINK_FACT.match(fact)]
    return clean_text(" ".join([*facts, profile.identity.headline or ""]))


def _years(profile: MasterProfileData) -> set[str]:
    """Les années des dates de début et de fin des expériences et des formations."""
    dated: list[Experience | Education] = [*profile.experiences, *profile.education]
    dates = [date for item in dated for date in (item.start, item.end)]
    return {date[:4] for date in dates if date}


def _words(text: str) -> list[tuple[str, int, int]]:
    """Les mots de `text` comparables (`normalize_term`) : `(mot, début, fin)` dans le texte."""
    return [
        (part, match.start(), match.end())
        for match in _WORD.finditer(text)
        for part in normalize_term(match.group(), plural=True).split()
    ]


def _number_claims(text: str, reference: set[str]) -> Found:
    unbacked = figures_in(text) - reference
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


def _ratio_claims(text: str, facts: str) -> Found:
    """Les proportions (« doublé », « moitié », « x3 ») que les faits ne disent pas, comme le
    validateur des modifications : même famille dans les faits, ou un chiffre de cette famille."""
    said, figures = ratio_families(facts), figures_in(facts)
    unbacked = {
        family
        for family in ratio_families(text)
        if family not in said and not RATIO_NUMBERS.get(family, frozenset()) & figures
    }
    found: Found = {}
    for match in _WORD.finditer(text):
        family = _RATIO_WORDS.get(normalize_term(match.group()))
        if family in unbacked:
            found.setdefault(("number", family), (match.start(), Claim("number", match.group())))
    for match in _TIMES.finditer(text):
        written = {claim.term for _, claim in found.values()}
        if ratio_families(match.group()) & unbacked and match.group() not in written:
            found.setdefault(
                ("number", match.group()), (match.start(), Claim("number", match.group()))
            )
    for family in unbacked - _families(found):  # en toutes lettres (« divisé par deux »)
        found.setdefault(("number", family), (len(text), Claim("number", family)))
    return found


def _families(found: Found) -> set[str]:
    return {family for _, claim in found.values() for family in ratio_families(claim.term)}


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
            found.setdefault(("tool", form), (start, Claim("tool", text[start : window[-1][2]])))
    return found


def _same_clause(text: str, left: re.Match[str], right: re.Match[str]) -> bool:
    return _CLAUSE_BREAK.search(text, left.end(), right.start()) is None


def _title_claims(text: str, known_titles: str) -> Found:
    """Les mots de titre que le texte se donne : lus dans les mots qui suivent une formule
    d'attribution (« en tant que », « je suis », « comme », « as a »), dans la même proposition."""
    matches = list(_WORD.finditer(text))
    words = [normalize_term(m.group()) for m in matches]
    found: Found = {}
    for rank in range(len(matches)):
        for cue in SELF_CUES:
            if tuple(words[rank : rank + len(cue)]) != cue:
                continue
            first = rank + len(cue)
            previous = matches[first - 1]
            for follow in matches[first : first + _SELF_WINDOW]:
                if not _same_clause(text, previous, follow):
                    break
                previous = follow
                form = normalize_term(follow.group(), plural=True)
                if form in _TITLES and f" {form} " not in known_titles:
                    found.setdefault(
                        ("title", form), (follow.start(), Claim("title", follow.group()))
                    )
    return found


def _title_texts(profile: MasterProfileData) -> str:
    texts = [experience.role for experience in profile.experiences]
    texts += [line.text for line in (profile.title,) if line is not None]
    return _padded(" ".join([*texts, profile.identity.headline or ""]))


def text_claims(
    text: str, profile: MasterProfileData, *, allowed: Sequence[str] = ()
) -> list[Claim]:
    """Les chiffres, proportions, outils, titres et noms propres de `text` que le profil ne dit
    pas, sans doublon, dans l'ordre du texte. `allowed` : des expressions entières (entreprise,
    intitulé exact de l'offre, nom d'un contact), jamais des outils ni des chiffres de l'offre."""
    clean = mask_own_contacts(clean_text(text), profile)
    body = mask_dates(mask_phrases(clean, allowed))
    facts = _fact_text(profile)
    known = _padded(" ".join(_strings(profile.model_dump())))
    found = _number_claims(body, figures_in(facts) | _years(profile))
    found |= _ratio_claims(body, facts)
    found |= _tool_claims(body, known)
    found |= _title_claims(body, _title_texts(profile))
    taken = {form for _, form in found} | {tok for _, form in found for tok in form.split()}
    for position, word in name_claims(body, known):
        form = normalize_term(word, plural=True)
        if form not in taken and form not in GREETINGS:
            found[("name", form)] = (position, Claim("name", word))
    return [claim for _, claim in sorted(found.values(), key=lambda item: item[0])]
