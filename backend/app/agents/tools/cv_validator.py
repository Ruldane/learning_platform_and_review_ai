"""Validator of CV changes against the master profile (SPEC 5.5, criterion 18.3): code,
not an agent. A proposal never becomes a fact: everything its `after` text says must already be
said by the facts it cites or by the profile's skills.

Rules, in order (each adds a reason, never the CV text):
0. no profile fact supports it -> "to confirm";
1. a number ("30 %", "1 000", "1,5", "trente") absent from the cited facts or attached to
   a measure that the facts do not let it identify;
2. a proportion ("moitié", "tiers", "x2") without a figure of the same family in the facts;
3. a lexicon tool, an offer term (tools, keywords) or a proper noun, absent from the cited facts and
   the skills: an offer term -> "gap" (it never enters the CV), other -> "to
   confirm";
4. a title word ("lead", "senior"...) or the offer's job title absent from the profile's roles;
5. a structured fact (title, role, degree, language and level, skill, link) of which a word or
   the URL is not in the targeted fact itself (the profile's roles count only for the title):
   citing a neighboring fact does not lift this rule (`cv_validator_facts`).

"Gap" wins over "to confirm", which wins over "ok". `remove` and `move` write
no text: always "ok". Terms are compared as whole words, without case or accent, up to a simple
plural (`normalize_term`)."""

import re
from dataclasses import dataclass
from typing import Literal

from app.agents.tools.cv_lexicon import (
    AMBIGUOUS_TERMS,
    RATIO_NUMBERS,
    TECH_TERMS,
    TITLE_WORDS,
    clean_text,
    figures_in,
    ratio_families,
)
from app.agents.tools.cv_numeric_claims import numeric_claims_supported
from app.agents.tools.cv_schema import MasterProfileData, facts_of
from app.agents.tools.cv_validator_facts import FOREIGN, is_structured, unbacked
from app.agents.tools.posting_schema import PostingAnalysis, normalize_term
from app.agents.tools.review_schema import Proposal

VerdictStatus = Literal["ok", "to_confirm", "to_gap"]

NO_FACT = "Your profile has no evidence for this change"
NUMBER = "Number missing from your profile"
RATIO = "Proportion with no supporting number in your profile"
NUMERIC_ASSOCIATION = "Confirm what this number measures"
TOOL = "Tool missing from your profile"
NAME = "Proper name missing from your profile"
TITLE = "Title missing from your profile"
GAP = "Posting keyword unsupported by the cited facts or skills. See the skill gap."

_TECH = {normalize_term(term, plural=True): term for term in TECH_TERMS}
_TITLE_WORDS = {normalize_term(word, plural=True) for word in TITLE_WORDS}
_WORD = re.compile(r"\w[\w+#]*")
_SENTENCE_END = ".!?\n"  # neither ":" nor ";": "Stack: Streamlit" names a tool
_BULLETS = " \t\n-•*–—«\"'("
_MIN_NAME = 3
_AMBIGUOUS = {
    normalize_term(term, plural=True): frozenset(normalize_term(q) for q in qualifiers)
    for term, qualifiers in AMBIGUOUS_TERMS.items()
}


@dataclass(frozen=True)
class Verdict:
    status: VerdictStatus
    blocks: list[str]
    gap_terms: list[str]


def _padded(text: str) -> str:
    return f" {normalize_term(text, plural=True)} "


def cited_facts(p: Proposal, facts: dict[str, str]) -> list[str]:
    """The text of the facts the proposal cites (`target` first), without duplicates."""
    ids = dict.fromkeys(fact for fact in (p.target, *p.fact_ids) if fact)
    return [facts[fact] for fact in ids if fact in facts]


def _unbacked_ratios(after: str, reference: str) -> bool:
    """A proportion in `after` that the facts state neither by the same word nor by a figure."""
    said = ratio_families(reference)
    figures = figures_in(reference)
    return any(
        family not in said and not RATIO_NUMBERS.get(family, frozenset()) & figures
        for family in ratio_families(after)
    )


def _posting_terms(analysis: PostingAnalysis) -> dict[str, str]:
    """Offer tools and keywords (and variants): compared form -> the offer's wording."""
    terms: dict[str, str] = {}
    for tool in analysis.tools:
        terms.setdefault(normalize_term(tool, plural=True), tool)
    for keyword in analysis.keywords:
        for form in (keyword.term, *keyword.variants):
            terms.setdefault(normalize_term(form, plural=True), keyword.term)
    terms.pop("", None)
    return terms


def _starts_sentence(text: str, match: re.Match[str]) -> bool:
    before = text[: match.start()].rstrip(_BULLETS)
    return not before or before[-1] in _SENTENCE_END


def product_forms(after: str) -> set[str]:
    """Ambiguous terms ("vue", "spring", "rest"...) that `after` writes in their product form:
    a capitalized word not at the start of a sentence (or an acronym, "REST"), or followed by
    qualificatif (« vue.js », « spring boot »)."""
    words = list(_WORD.finditer(after))
    found: set[str] = set()
    for rank, match in enumerate(words):
        word = match.group()
        form = normalize_term(word, plural=True)
        if form not in _AMBIGUOUS:
            continue
        following = normalize_term(words[rank + 1].group()) if rank + 1 < len(words) else ""
        shouted = word.isupper() and len(word) > 1
        capital = word[0].isupper() and (shouted or not _starts_sentence(after, match))
        if capital or following in _AMBIGUOUS[form]:
            found.add(form)
    return found


def _term_findings(
    after: str, known: str, profile: MasterProfileData, analysis: PostingAnalysis
) -> tuple[list[str], list[str]]:
    """`(offer terms, other tools)` present in `after` and absent from the cited facts and
    the profile's skills (`known`: the text of the facts). Offer terms are returned as the offer
    writes them."""
    haystack = _padded(after)
    skills = _padded(" ".join(skill.name for skill in profile.skills))
    posting = _posting_terms(analysis)
    product = product_forms(after)
    gap: dict[str, str] = {}
    tools: list[str] = []
    for form, label in {**_TECH, **posting}.items():
        if f" {form} " not in haystack or f" {form} " in known or f" {form} " in skills:
            continue
        if form in _AMBIGUOUS and form not in posting and form not in product:
            continue
        if form in posting:
            gap.setdefault(normalize_term(label), label)
        else:
            tools.append(label)
    return list(gap.values()), tools


def _title_texts(profile: MasterProfileData) -> list[str]:
    texts = [experience.role for experience in profile.experiences]
    texts += [line.text for line in (profile.title,) if line is not None]
    texts.append(profile.identity.headline or "")
    return texts


def _titles(profile: MasterProfileData) -> str:
    return _padded(" ".join(_title_texts(profile)))


def _known_titles(p: Proposal, profile: MasterProfileData) -> str:
    """The profile's roles and titles count only to rewrite the title (`t…`): another role
    would raise "Lead" or "Senior" on an experience, a skill or a language."""
    return " ".join(_title_texts(profile)) if (p.target or "").startswith("t") else ""


def _title_claimed(after: str, profile: MasterProfileData, analysis: PostingAnalysis) -> bool:
    """A title word or the offer's job title in `after`, absent from the profile's roles."""
    known = _titles(profile)
    haystack = _padded(after)
    if any(f" {w} " in haystack and f" {w} " not in known for w in _TITLE_WORDS):
        return True
    posting = normalize_term(re.sub(r"\([^)]*\)", " ", analysis.title), plural=True)
    return bool(posting) and f" {posting} " in haystack and f" {posting} " not in known


def capitalized_names(after: str, known: str, *, skip_first: bool) -> list[tuple[int, str]]:
    """Capitalized words of `after` (not at the start of a sentence, not acronyms) that `known` (a
    `_padded` text) does not contain, one per compared form: `(position, word as written)`."""
    found: dict[str, tuple[int, str]] = {}
    for match in _WORD.finditer(after):
        word = match.group()
        if _starts_sentence(after, match) and (skip_first or match.start() > 0):
            continue
        if len(word) < _MIN_NAME or not word[0].isupper() or word.isupper():
            continue
        form = normalize_term(word, plural=True)
        if f" {form} " not in known:
            found.setdefault(form, (match.start(), word))
    return list(found.values())


def _names(after: str, profile: MasterProfileData, *, skip_first: bool) -> set[str]:
    """Capitalized words of `after` (not at the start of a sentence, not acronyms) that no text
    of the profile contains: a tool or a company no list knows."""
    known = _padded(" ".join(facts_of(profile).values()))
    places = [experience.location or "" for experience in profile.experiences]
    known += _padded(" ".join([profile.identity.name, profile.identity.location or "", *places]))
    return {
        normalize_term(word, plural=True)
        for _, word in capitalized_names(after, known, skip_first=skip_first)
    }


def validate(p: Proposal, profile: MasterProfileData, analysis: PostingAnalysis) -> Verdict:
    """Return the verdict for a proposed CV edit.

    `blocks` contains fixed English reasons. `gap_terms` preserves the posting's keywords that
    lack support in the cited facts. A keyword can appear elsewhere in the profile.
    """
    if p.action in ("remove", "move"):
        return Verdict("ok", [], [])
    facts = facts_of(profile)
    cited = cited_facts(p, facts)
    after = clean_text(p.after)
    reference = clean_text(" ".join(cited))
    own = clean_text(facts.get(p.target or "", ""))  # the targeted fact alone (I-1)
    blocks: list[str] = [] if cited else [NO_FACT]
    if figures_in(after) - figures_in(reference):
        blocks.append(NUMBER)
    if _unbacked_ratios(after, reference):
        blocks.append(RATIO)
    if NUMBER not in blocks and RATIO not in blocks and not numeric_claims_supported(after, cited):
        blocks.append(NUMERIC_ASSOCIATION)
    gap, tools = _term_findings(after, _padded(reference), profile, analysis)
    if tools:
        blocks.append(TOOL)
    if gap:
        blocks.append(GAP)
    if _title_claimed(after, profile, analysis):
        blocks.append(TITLE)
    skip_first = p.section not in ("skills", "languages", "links")
    seen = {tok for term in [*gap, *tools] for tok in normalize_term(term, plural=True).split()}
    if _names(after, profile, skip_first=skip_first) - seen:
        blocks.append(NAME)
    if is_structured(p) and unbacked(after, own, _known_titles(p, profile)):
        blocks.append(FOREIGN)
    status: VerdictStatus = "to_gap" if gap else "to_confirm" if blocks else "ok"
    return Verdict(status, blocks, gap)
