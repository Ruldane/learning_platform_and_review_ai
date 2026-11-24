"""Le contrôle des faits structurés du validateur (SPEC 5.5, critère 18.3, revue finale BA-C1) :
l'intitulé d'une expérience, d'un diplôme, d'un projet, le titre, une compétence, une langue et
son niveau, un lien. Ce ne sont pas des phrases libres : un mot de plus (« Ingénieure » pour
« Développeuse », « Master » pour « Licence », « C1 » pour « B2 », « expert » pour une
compétence) est un fait que le profil ne dit pas, et une URL n'est jamais réécrite.

Règle : chaque mot significatif de `after` figure dans le fait visé lui-même ou dans les rôles
et titres du profil (jamais dans un fait voisin cité, qui lèverait « C1 » ou « Master » ; mots
entiers, sans casse ni accent, pluriel simple près ; le féminin n'est pas le masculin) ; chaque
lien ou nom de domaine écrit dans `after` est celui du fait visé, à l'identique (schéma ajouté
quand il manque, hôte sans casse, fin d'URL avec sa casse). Sinon le bloc
fixe `FOREIGN` (« à confirmer »)."""

import re

from app.agents.tools.posting_schema import normalize_term
from app.agents.tools.review_schema import Proposal

FOREIGN = "Wording missing from the corresponding fact in your profile"

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


def significant_words(text: str) -> set[str]:
    """Les mots significatifs : hors mots outils, hors nombres seuls (règle des chiffres)."""
    words = normalize_term(text, plural=True).split()
    return {w for w in words if w not in _STOP_WORDS and not w.isdigit()}


def _link_form(raw: str) -> str:
    """Un lien sous une forme comparable (D137 n° 6) : le schéma (`https` s'il manque) et l'hôte
    sans casse, le reste de l'URL tel qu'écrit (« /Camille » n'est pas « /camille »), sans
    ponctuation ni barre finale."""
    link = raw.rstrip(_LINK_END)
    scheme, found, rest = link.partition("://")
    if not found:
        scheme, rest = "https", link
    host, slash, path = rest.partition("/")
    return f"{scheme.casefold()}://{host.casefold()}{slash}{path}"


def _links_of(text: str) -> set[str]:
    return {_link_form(m.group()) for m in _LINK.finditer(text)}


def unbacked(after: str, reference: str, titles: str) -> bool:
    """`after` dit un mot ou un lien que `reference` (le texte du fait visé seul) et `titles` (les
    rôles et titres du profil) ne disent pas."""
    known = significant_words(f"{reference} {titles}")
    if significant_words(after) - known:
        return True
    return bool(_links_of(after) - _links_of(reference))
