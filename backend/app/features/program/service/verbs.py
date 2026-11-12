"""Verbe d'action en tête d'un titre de tâche (SPEC 3.4) : une règle simple, sans dictionnaire."""

import re

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


def has_action_verb(title: str) -> bool:
    """Le premier mot finit par -er, -ir, -re, -oir ou figure dans `ACTION_VERBS`."""
    match = _WORD.match(title.strip())
    if match is None:
        return False
    word = match.group().casefold()
    return word.endswith(INFINITIVE_ENDINGS) or word in ACTION_VERBS
