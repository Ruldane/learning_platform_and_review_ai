"""The check of the validator's structured facts (SPEC 5.5, criterion 18.3, final review BA-C1):
the title of an experience, a degree, a project, the title, a skill, a language and
its level, a link. These are not free sentences: one extra word ("Ingénieure" for
"Développeuse", "Master" for "Licence", "C1" for "B2", "expert" for a
skill) is a fact the profile does not state, and a URL is never rewritten.

Rule: each significant word of `after` appears in the targeted fact itself or in the roles
and titles of the profile (never in a neighboring cited fact, which would lift "C1" or "Master";
words, without case or accent, simple plural aside; the feminine is not the masculine); each
link or domain name written in `after` is that of the targeted fact, identical (scheme added
when missing, host in lower case, end of URL with its case). Otherwise the block
sets `FOREIGN` ("to confirm")."""

import re

from app.agents.tools.posting_schema import normalize_term
from app.agents.tools.review_schema import Proposal

FOREIGN = "Wording missing from the corresponding fact in your profile"

_STRUCTURED = re.compile(r"^[xfpctlk]\d+$")
# A link or a domain name ("github.com/name", "https://...", "www....", "node.js").
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
    """The target is a structured fact (not an achievement, a detail, nor the summary)."""
    return bool(p.target) and _STRUCTURED.match(p.target or "") is not None


def significant_words(text: str) -> set[str]:
    """Significant words: excluding function words, excluding numbers alone (number rule)."""
    words = normalize_term(text, plural=True).split()
    return {w for w in words if w not in _STOP_WORDS and not w.isdigit()}


def _link_form(raw: str) -> str:
    """A link in a comparable form (D137 no. 6): the scheme (`https` if missing) and the host
    in lower case, the rest of the URL as written ("/Camille" is not "/camille"), without
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
    """`after` says a word or a link that `reference` (the targeted fact's text alone) and `titles`
    (the profile's roles and titles) do not say."""
    known = significant_words(f"{reference} {titles}")
    if significant_words(after) - known:
        return True
    return bool(_links_of(after) - _links_of(reference))
