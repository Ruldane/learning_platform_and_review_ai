"""Verbe d'action en tête d'un titre de tâche (SPEC 3.4) : une règle simple, sans dictionnaire.
Aussi : le sujet d'une révision, sans le préfixe de révision que le titre du module porte déjà."""

import re
import unicodedata

INFINITIVE_ENDINGS = ("er", "ir", "re", "oir")
# Formes qui n'ont pas la terminaison d'un infinitif (impératifs usuels des consignes).
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
    ]
)
_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
# « Réviser », « Révision de », « Revoir » en tête, casse et accents ignorés, suivis de « : » ou
# d'une espace (« Révisions générales » ou « Revoiture » ne sont pas des préfixes).
_E = "[eéèêë]"
_REVIEW_PREFIX = re.compile(
    rf"^\s*(?:r{_E}vis(?:er|ion\s+de)|r{_E}voir)(?:\s*:\s*|\s+)", re.IGNORECASE
)


def review_subject(title: str) -> str:
    """Le titre d'un module sans son préfixe de révision : « Réviser Python » → « Python »
    (D98 : jamais « Réviser : Réviser Python »). Un titre réduit au préfixe reste tel quel."""
    text = unicodedata.normalize("NFC", title)
    rest = _REVIEW_PREFIX.sub("", text, count=1).strip()
    return rest[:1].upper() + rest[1:] if rest else title


def has_action_verb(title: str) -> bool:
    """Le premier mot finit par -er, -ir, -re, -oir ou figure dans `ACTION_VERBS`."""
    match = _WORD.match(title.strip())
    if match is None:
        return False
    word = match.group().casefold()
    return word.endswith(INFINITIVE_ENDINGS) or word in ACTION_VERBS
