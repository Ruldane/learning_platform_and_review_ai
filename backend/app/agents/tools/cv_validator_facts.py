"""Le contrôle des faits structurés du validateur (SPEC 5.5, critère 18.3, revue finale BA-C1) :
l'intitulé d'une expérience, d'un diplôme, d'un projet, le titre, une compétence, une langue et
son niveau, un lien. Ce ne sont pas des phrases libres : un mot de plus (« Ingénieure » pour
« Développeuse », « Master » pour « Licence », « C1 » pour « B2 », « expert » pour une
compétence) est un fait que le profil ne dit pas, et une URL n'est jamais réécrite.

Règle : chaque mot significatif de `after` figure dans le fait visé lui-même ou dans les rôles
et titres du profil (jamais dans un fait voisin cité, qui lèverait « C1 » ou « Master » ; mots
entiers, sans casse ni accent, pluriel simple près ; le féminin n'est pas le masculin) ; chaque
lien ou nom de domaine écrit dans `after` est celui du fait visé, à l'identique. Sinon le bloc
fixe `FOREIGN` (« à confirmer »)."""

import re

from app.agents.tools.posting_schema import normalize_term
from app.agents.tools.review_schema import Proposal

FOREIGN = "Intitulé absent de ton profil"

_STRUCTURED = re.compile(r"^[xfpctlk]\d+$")
# Un lien ou un nom de domaine (« github.com/nom », « https://… », « www.… », « node.js »).
_LINK = re.compile(r"[^\s\"'<>()]*://[^\s\"'<>()]+|[\w-]+(?:\.[\w-]+)+(?:/[^\s\"'<>()]*)?")
_LINK_END = ".,;:!?/"
_STOP_WORDS = frozenset(
    {
        "de",
        "du",
        "des",
        "d",
        "la",
        "le",
        "les",
        "l",
        "un",
        "une",
        "et",
        "ou",
        "en",
        "au",
        "aux",
        "a",
        "chez",
        "pour",
        "par",
        "avec",
        "sur",
        "dans",
        "the",
        "of",
        "and",
        "at",
        "in",
        "for",
        "to",
        "with",
        "an",
        "by",
        "on",
        "as",
    }
)


def is_structured(p: Proposal) -> bool:
    """La cible est un fait structuré (pas une réalisation, un détail, ni le résumé)."""
    return bool(p.target) and _STRUCTURED.match(p.target or "") is not None


def _significant(text: str) -> set[str]:
    """Les mots significatifs : hors mots outils, hors nombres seuls (règle des chiffres)."""
    words = normalize_term(text, plural=True).split()
    return {w for w in words if w not in _STOP_WORDS and not w.isdigit()}


def _links_of(text: str) -> set[str]:
    return {m.group().rstrip(_LINK_END).casefold() for m in _LINK.finditer(text)}


def unbacked(after: str, reference: str, titles: str) -> bool:
    """`after` dit un mot ou un lien que `reference` (le texte du fait visé seul) et `titles` (les
    rôles et titres du profil) ne disent pas."""
    known = _significant(f"{reference} {titles}")
    if _significant(after) - known:
        return True
    return bool(_links_of(after) - _links_of(reference))
