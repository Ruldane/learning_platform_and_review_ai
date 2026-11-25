"""Recognize task titles that start with an action verb and strip review prefixes (SPEC 3.4)."""

import re
import unicodedata

INFINITIVE_ENDINGS = ("er", "ir", "re", "oir")
# English verbs and French imperatives used in existing plans.
ACTION_VERBS = frozenset(
    [
        "lis",
        "écris",
        "fais",
        "crée",
        "teste",
        "vérifie",
        "implémente",
        "réalise",
        "complète",
        "résous",
        "applique",
        "compare",
        "explique",
        "rédige",
        "dessine",
        "installe",
        "configure",
        "lance",
        "exécute",
        "analyse",
        "résume",
        "trouve",
        "identifie",
        "choisis",
        "construis",
        "prends",
        "mets",
        "suis",
        "entraîne",
        "apprends",
        "note",
        "révise",
        "décris",
        "définis",
        "reproduis",
        "améliore",
        "documente",
        "publie",
        "déploie",
        "génère",
        "calcule",
        "mesure",
        "évalue",
        "présente",
        "rends",
        "add",
        "analyse",
        "analyze",
        "apply",
        "build",
        "calculate",
        "choose",
        "code",
        "compare",
        "complete",
        "configure",
        "connect",
        "create",
        "debug",
        "define",
        "deploy",
        "describe",
        "design",
        "document",
        "draw",
        "evaluate",
        "explain",
        "explore",
        "find",
        "fix",
        "generate",
        "identify",
        "implement",
        "inspect",
        "install",
        "launch",
        "measure",
        "outline",
        "practice",
        "practise",
        "prepare",
        "publish",
        "read",
        "refactor",
        "reproduce",
        "research",
        "review",
        "run",
        "solve",
        "study",
        "summarise",
        "summarize",
        "take",
        "test",
        "train",
        "try",
        "use",
        "validate",
        "verify",
        "watch",
        "write",
    ]
)
_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
# "Réviser", "Révision de", "Revoir" or "Review (of)" at the start, case and accents ignored,
# followed by ":" or a space ("Révisions générales" or "Revoiture" are not prefixes).
_E = "[eéèêë]"
_REVIEW_PREFIX = re.compile(
    rf"^\s*(?:r{_E}vis(?:er|ion\s+de)|r{_E}voir|review(?:\s+of)?)(?:\s*:\s*|\s+)", re.IGNORECASE
)


def review_subject(title: str) -> str:
    """The title of a module without its review prefix: "Réviser Python" → "Python"
    (D98: never "Review: Réviser Python"). A title reduced to the prefix stays as it is."""
    text = unicodedata.normalize("NFC", title)
    rest = _REVIEW_PREFIX.sub("", text, count=1).strip()
    return rest[:1].upper() + rest[1:] if rest else title


def has_action_verb(title: str) -> bool:
    """Match an action verb or a French infinitive in the first word."""
    match = _WORD.match(title.strip())
    if match is None:
        return False
    word = match.group().casefold()
    return word.endswith(INFINITIVE_ENDINGS) or word in ACTION_VERBS
