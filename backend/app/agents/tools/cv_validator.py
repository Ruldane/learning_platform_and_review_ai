"""Validateur des modifications de CV contre le profil maître (SPEC 5.5, critère 18.3) : du code,
pas un agent. Une proposition ne devient jamais un fait : tout ce que dit son texte `after` doit
être déjà dit par les faits qu'elle cite ou par les compétences du profil.

Règles, dans l'ordre (chacune ajoute une raison, jamais le texte du CV) :
0. aucun fait du profil ne l'appuie → « à confirmer » ;
1. un nombre (« 30 % », « 1 000 », « 1,5 », « trente ») absent des faits cités ou rattaché à
   une mesure que les faits ne permettent pas d'identifier ;
2. une proportion (« moitié », « tiers », « x2 ») sans chiffre de la même famille dans les faits ;
3. un outil du lexique, de l'offre (outils, mots clés) ou un nom propre, absent des faits cités et
   des compétences : terme de l'offre → « écart » (il n'entre jamais dans le CV), autre → « à
   confirmer » ;
4. un mot de titre (« lead », « senior »…) ou l'intitulé de l'offre absent des rôles du profil ;
5. un fait structuré (titre, rôle, diplôme, langue et niveau, compétence, lien) dont un mot ou
   l'URL n'est pas dans le fait visé lui-même (les rôles du profil ne comptent que pour le titre) :
   citer un fait voisin ne lève pas cette règle (`cv_validator_facts`).

« Écart » l'emporte sur « à confirmer », qui l'emporte sur « ok ». `remove` et `move` n'écrivent
aucun texte : toujours « ok ». Les termes sont comparés mots entiers, sans casse ni accent, au
pluriel simple près (`normalize_term`)."""

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

NO_FACT = "Aucun fait de ton profil n'appuie cette modification"
NUMBER = "Chiffre absent de ton profil"
RATIO = "Proportion sans chiffre dans ton profil"
NUMERIC_ASSOCIATION = "Lien entre un chiffre et sa mesure à confirmer"
TOOL = "Outil absent de ton profil"
NAME = "Nom propre absent de ton profil"
TITLE = "Titre absent de ton profil"
GAP = "Mot clé de l'offre absent des faits cités et de tes compétences : il part vers l'écart"

_TECH = {normalize_term(term, plural=True): term for term in TECH_TERMS}
_TITLE_WORDS = {normalize_term(word, plural=True) for word in TITLE_WORDS}
_WORD = re.compile(r"\w[\w+#]*")
_SENTENCE_END = ".!?\n"  # ni « : » ni « ; » : « Stack : Streamlit » nomme un outil
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
    """Le texte des faits que la proposition cite (`target` d'abord), sans doublon."""
    ids = dict.fromkeys(fact for fact in (p.target, *p.fact_ids) if fact)
    return [facts[fact] for fact in ids if fact in facts]


def _unbacked_ratios(after: str, reference: str) -> bool:
    """Une proportion de `after` que les faits ne disent ni par le même mot ni par un chiffre."""
    said = ratio_families(reference)
    figures = figures_in(reference)
    return any(
        family not in said and not RATIO_NUMBERS.get(family, frozenset()) & figures
        for family in ratio_families(after)
    )


def _posting_terms(analysis: PostingAnalysis) -> dict[str, str]:
    """Outils et mots clés de l'offre (et variantes) : forme comparée → formulation de l'offre."""
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
    """Les termes ambigus (« vue », « spring », « rest »…) que `after` écrit sous leur forme de
    produit : un mot capitalisé hors début de phrase (ou un sigle, « REST »), ou suivi d'un
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
    """`(termes de l'offre, autres outils)` présents dans `after` et absents des faits cités et
    des compétences du profil (`known` : le texte des faits). Les termes de l'offre sont rendus
    tels que l'offre les écrit."""
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
    """Les rôles et titres du profil ne comptent que pour réécrire le titre (`t…`) : un autre rôle
    lèverait « Lead » ou « Senior » sur une expérience, une compétence ou une langue."""
    return " ".join(_title_texts(profile)) if (p.target or "").startswith("t") else ""


def _title_claimed(after: str, profile: MasterProfileData, analysis: PostingAnalysis) -> bool:
    """Un mot de titre ou l'intitulé de l'offre dans `after`, absent des rôles du profil."""
    known = _titles(profile)
    haystack = _padded(after)
    if any(f" {w} " in haystack and f" {w} " not in known for w in _TITLE_WORDS):
        return True
    posting = normalize_term(re.sub(r"\([^)]*\)", " ", analysis.title), plural=True)
    return bool(posting) and f" {posting} " in haystack and f" {posting} " not in known


def capitalized_names(after: str, known: str, *, skip_first: bool) -> list[tuple[int, str]]:
    """Les mots capitalisés de `after` (hors début de phrase, hors sigles) que `known` (un texte
    `_padded`) ne contient pas, un par forme comparée : `(position, mot tel qu'écrit)`."""
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
    """Les mots capitalisés de `after` (hors début de phrase, hors sigles) qu'aucun texte du
    profil ne contient : un outil ou une entreprise qu'aucune liste ne connaît."""
    known = _padded(" ".join(facts_of(profile).values()))
    places = [experience.location or "" for experience in profile.experiences]
    known += _padded(" ".join([profile.identity.name, profile.identity.location or "", *places]))
    return {
        normalize_term(word, plural=True)
        for _, word in capitalized_names(after, known, skip_first=skip_first)
    }


def validate(p: Proposal, profile: MasterProfileData, analysis: PostingAnalysis) -> Verdict:
    """Le verdict sur une proposition : voir l'en-tête du module. `blocks` : des raisons fixes en
    français, jamais le texte du CV ; `gap_terms` : les mots clés de l'offre que les faits cités
    ne portent pas, comme l'offre les écrit : à appuyer par un fait ou à acquérir (ils peuvent
    figurer ailleurs dans le profil : un terme est « à l'écart » quand le fait cité ne le dit pas,
    pas quand le profil entier l'ignore)."""
    if p.action in ("remove", "move"):
        return Verdict("ok", [], [])
    facts = facts_of(profile)
    cited = cited_facts(p, facts)
    after = clean_text(p.after)
    reference = clean_text(" ".join(cited))
    own = clean_text(facts.get(p.target or "", ""))  # le fait visé seul (I-1)
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
