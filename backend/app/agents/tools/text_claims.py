"""Checks the facts of a text written in January's name (SPEC 1, 18.3, F16): pieces of the
application kit, follow-up drafts, pitch, form answers, improved answer of the debrief.
Code, not an agent: a figure, a tool, a title or a proper noun that the validated master profile
does not state is returned (`Claim`), and the piece stays "to verify" with these terms. Better to
over-report (a human decides) than let an invented fact through.

Readings of the CV change validator (`cv_validator`, `cv_lexicon`):
- **numbers** (digits and letters, "30 %", "12 k€") and **proportions** ("doublé", "x3")
  absent from the texts of the profile's facts (titles, lines, achievements, summary, education
  details, skills, languages) and from the years of their start and end dates. Never the
  digits of a phone, an email or a link, nor the months: they are not facts;
- **tools** from the lexicon, case-insensitive (an ambiguous term like "vue" only as a product),
  absent from the profile;
- **titles** ("lead", "senior"...) absent from the profile's job titles, only when the text
  attributes them to itself ("en tant que", "je suis", "comme", "as a"...);
- **noms propres** (`text_claims_names`).

`allowed` only contains whole expressions: the company, the exact title of the offer, the
name of a contact. An expression is removed from the text where it appears (`text_claims_mask`):
everywhere for names, and for the rest only when a word of the offer or the employer precedes it
("votre poste de Développeuse IA", "chez Société Fictive"): "en tant que Lead Data" stays read.
Tools and keywords of the offer have no place here, nor any figure: they are never a fact of
January's. The sentences must talk about January."""

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
_SKIPPED_KEYS = frozenset({"id", "sources"})  # identifiers and origins: not January's text
_LINK_FACT = re.compile(r"^k\d+$")  # a link: its address is not a reference for figures
_CLAUSE_BREAK = re.compile(r"[.,;:!?\n]")
_TIMES = re.compile(r"(?<!\w)(?:[x×]\s?\d+|\d+\s?[x×])(?!\w)", re.IGNORECASE)
_SELF_WINDOW = 6  # words after the formula where a title word is read


def _tech_by_first_word() -> dict[str, list[tuple[str, tuple[str, ...]]]]:
    """The lexicon tools, compared (`normalize_term`), filed by their first word."""
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
    """A term of the text that the profile does not state, as the text writes it (a number in its
    canonical form: "30%", "1000"; a proportion, the word written: "doublé")."""

    kind: ClaimKind
    term: str


Found = dict[tuple[ClaimKind, str], tuple[int, Claim]]  # (kind, key) → (position, claim)


def _strings(value: Any) -> Iterator[str]:
    """The texts of a profile (`model_dump`), without identifiers or origins."""
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
    """The texts of the facts (excluding links) and the header title: the reference for figures and
    proportions. Months and contact figures are not in it."""
    facts = [text for fact, text in facts_of(profile).items() if not _LINK_FACT.match(fact)]
    return clean_text(" ".join([*facts, profile.identity.headline or ""]))


def _years(profile: MasterProfileData) -> set[str]:
    """The years of the start and end dates of the experiences and education."""
    dated: list[Experience | Education] = [*profile.experiences, *profile.education]
    dates = [date for item in dated for date in (item.start, item.end)]
    return {date[:4] for date in dates if date}


def _words(text: str) -> list[tuple[str, int, int]]:
    """Comparable words of `text` (`normalize_term`): `(word, start, end)` positions in the text."""
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
    """The proportions ("doublé", "moitié", "x3") that the facts do not state, like the
    validator of CV changes: same family in the facts, or a figure of that family."""
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
    for family in unbacked - _families(found):  # written out in full ("divisé par deux")
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
    """The title words the text gives itself: read in the words following an attribution
    formula ("en tant que", "je suis", "comme", "as a"), within the same clause."""
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
    """The figures, proportions, tools, titles and proper nouns of `text` that the profile does
    not state, without duplicates, in text order. `allowed`: whole expressions (company, exact
    title of the offer, name of a contact), never tools or figures of the offer."""
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
