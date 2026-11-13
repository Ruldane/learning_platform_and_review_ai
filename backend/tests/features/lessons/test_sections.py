"""Découpe d'une leçon 3.5 pour le Tuteur (`lesson_parts`, `lesson_sources`, D103)."""

from app.features.lessons.service.sections import lesson_parts, lesson_sources
from tests.support.lessons import URL_ONE, URL_TWO, lesson_markdown

TAUGHT = [
    "L'essentiel en 5 lignes",
    "Explication",
    "Schémas",
    "Exemple travaillé",
    "Erreurs fréquentes",
]


def test_lesson_parts_finds_structure() -> None:
    parts = lesson_parts(lesson_markdown(400))
    assert [title for title, _ in parts.sections] == TAUGHT
    assert parts.objectives == [
        "Comprendre le calcul des poids d'attention [1].",
        "Savoir lire un masque causal [2].",
    ]
    assert parts.exercise == "Calculer les poids d'attention d'une séquence de trois mots."
    assert parts.solution.startswith("Les poids valent une distribution")
    schemas = dict(parts.sections)["Schémas"]
    assert schemas.startswith("```mermaid") and schemas.endswith("```")
    essential = dict(parts.sections)["L'essentiel en 5 lignes"]
    assert essential.count("\n- ") == 4 and "## " not in essential


def test_titles_ignore_case_accents_and_curly_apostrophe() -> None:
    markdown = (
        "# Leçon\n\n## ERREURS FREQUENTES\n\nOubli.\n\n## L’essentiel en 5 lignes :\n\nA.\n\n"
        "## Schemas\n\nB.\n\n## exercice\n\nFais-le.\n\n## Corrige de l'exercice\n\nVoilà."
    )
    parts = lesson_parts(markdown)
    assert [title for title, _ in parts.sections] == [
        "L’essentiel en 5 lignes :",
        "Schemas",
        "ERREURS FREQUENTES",
    ]  # ordre de la séance, pas celui du document
    assert (parts.exercise, parts.solution) == ("Fais-le.", "Voilà.")


def test_heading_inside_code_does_not_split() -> None:
    markdown = (
        "## Explication\n\nAvant.\n\n```python\n## pas un titre\nx = 1\n```\n\nAprès.\n\n"
        "~~~\n## toujours pas\n~~~\n\n## Exercice\n\nÀ faire."
    )
    parts = lesson_parts(markdown)
    [(title, body)] = parts.sections
    assert title == "Explication" and "## pas un titre" in body and body.endswith("~~~")
    assert parts.exercise == "À faire." and parts.solution == ""


def test_missing_and_empty_sections_are_omitted() -> None:
    parts = lesson_parts("## Explication\n\n## Exemple travaillé\n\nUn exemple.\n### Détail\n\nX")
    assert parts.sections == [("Exemple travaillé", "Un exemple.\n### Détail\n\nX")]
    assert parts.objectives == [] and parts.exercise == "" and parts.solution == ""


def test_first_of_two_sections_wins() -> None:
    parts = lesson_parts("## Explication\n\nPremière.\n\n## Explication\n\nSeconde.")
    assert parts.sections == [("Explication", "Première.")]


def test_lesson_sources_are_numbered() -> None:
    assert lesson_sources(lesson_markdown(400)) == [
        (1, "Premier article", URL_ONE),
        (2, "Second article", URL_TWO),
    ]
    markdown = "## Sources\n\n2. Un livre sans lien\n1. [A](https://a.org)\n1. [B](https://b.org)"
    assert lesson_sources(markdown) == [(1, "A", "https://a.org"), (2, "Un livre sans lien", None)]
