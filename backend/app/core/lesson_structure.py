"""The headings for new lessons and the aliases used to read saved lessons."""

import unicodedata

OBJECTIVES = "Objectives"
PREREQUISITES = "Prerequisites"
KEY_POINTS = "Key points in 5 lines"
EXPLANATION = "Explanation"
DIAGRAMS = "Diagrams"
WORKED_EXAMPLE = "Worked example"
COMMON_MISTAKES = "Common mistakes"
EXERCISE = "Exercise"
SOLUTION = "Solution"
SOURCES = "Sources"
SELF_ASSESSMENT = "Self-assessment"

SECTIONS = (
    OBJECTIVES,
    PREREQUISITES,
    KEY_POINTS,
    EXPLANATION,
    DIAGRAMS,
    WORKED_EXAMPLE,
    COMMON_MISTAKES,
    EXERCISE,
    SOLUTION,
    SOURCES,
    SELF_ASSESSMENT,
)

LEGACY_SECTIONS = (
    "Objectifs",
    "Prérequis",
    "L'essentiel en 5 lignes",
    "Explication",
    "Schémas",
    "Exemple travaillé",
    "Erreurs fréquentes",
    "Exercice",
    "Corrigé de l'exercice",
    SOURCES,
    "Auto-évaluation",
)

_LEGACY_PREFIXES = {
    OBJECTIVES: "objectifs",
    PREREQUISITES: "prerequis",
    KEY_POINTS: "l'essentiel",
    EXPLANATION: "explication",
    DIAGRAMS: "schema",
    WORKED_EXAMPLE: "exemple travaille",
    COMMON_MISTAKES: "erreurs frequentes",
    EXERCISE: "exercice",
    SOLUTION: "corrige",
    SOURCES: "sources",
    SELF_ASSESSMENT: "auto-evaluation",
}


def reading_section(title: str) -> str | None:
    """Recognize a saved heading without changing the displayed title."""
    decomposed = unicodedata.normalize("NFKD", title.replace("’", "'"))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    folded = " ".join(plain.split()).rstrip(" :").casefold()
    return next(
        (
            name
            for name in SECTIONS
            if folded == name.casefold() or folded.startswith(_LEGACY_PREFIXES[name])
        ),
        None,
    )
