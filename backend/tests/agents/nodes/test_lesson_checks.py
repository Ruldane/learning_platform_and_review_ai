"""Contrôles déterministes d'une leçon (SPEC 3.5, D90) : structure, nombres, longueur, liens,
marqueurs et recopie. Pur, sans réseau ni modèle."""

import re

import pytest

from app.agents.nodes.verifier import MAX_QUOTE_WORDS, SECTIONS, check_lesson
from tests.support.lessons import SOURCE_ONE, SOURCES, TITLE, lesson_markdown

LONG_PASSAGE = " ".join(SOURCE_ONE.split()[:40])


def problems_of(markdown: str, *, title: str = TITLE) -> list[str]:
    return check_lesson(markdown, title=title, sources=SOURCES).problems


def drop_section(markdown: str, name: str) -> str:
    return re.sub(rf"## {re.escape(name)}\n.*?(?=\n## |\Z)", "", markdown, flags=re.DOTALL)


def with_section_text(markdown: str, name: str, extra: str) -> str:
    return re.sub(rf"(## {re.escape(name)}\n)", rf"\1\n{extra}\n", markdown, count=1)


def test_check_lesson_accepts_a_valid_lesson() -> None:
    result = check_lesson(lesson_markdown(1500), title=TITLE, sources=SOURCES)
    assert result.problems == [] and result.words == 1500


def test_sections_are_the_eleven_fixed_headings() -> None:
    assert len(SECTIONS) == 11 and SECTIONS[8] == "Corrigé de l'exercice"
    headings = re.findall(r"^## (.+)$", lesson_markdown(1500), flags=re.MULTILINE)
    assert tuple(headings) == SECTIONS


@pytest.mark.parametrize("words", [1200, 2500])
def test_word_limits_are_inclusive(words: int) -> None:
    assert problems_of(lesson_markdown(words)) == []


@pytest.mark.parametrize(
    ("mutation", "problem"),
    [
        ("drop:Corrigé de l'exercice", "Section manquante : « ## Corrigé de l'exercice »"),
        ("drop:Sources", "Section manquante"),
        ("objectives:4", "3 objectifs au plus"),
        ("words:900", "1 200"),
        ("words:2600", "2 500"),
        ("link:https://inconnu.example/page", "Lien absent des sources lues"),
        ("bare:https://inconnu.example/nu", "Lien absent des sources lues"),
        ("copy:40", "recopié"),
        ("no_mermaid", "schéma"),
        ("bad_mermaid", "Schéma Mermaid 1 refusé"),
        ("marker:7", "Marqueur [7] inconnu"),
        ("essential:4", "« L'essentiel en 5 lignes » compte 4"),
        ("selftest:4", "L'auto-évaluation compte 4"),
        ("title:Autre titre", "Titre « # Attention multi-têtes » absent"),
        ("extra_section", "Section en trop"),
        ("swap", "désordre"),
        ("long_quote", "Citation de plus de 25 mots"),
    ],
)
def test_check_lesson_reports(mutation: str, problem: str) -> None:
    kind, _, arg = mutation.partition(":")
    lesson = lesson_markdown(2600 if kind == "words" and arg == "2600" else 1500)
    if kind == "words":
        lesson = lesson_markdown(int(arg))
    elif kind == "drop":
        lesson = drop_section(lesson, arg)
    elif kind == "objectives":
        lesson = with_section_text(lesson, "Objectifs", "- Un\n- Deux\n- Trois\n- Quatre")
    elif kind == "link":
        lesson += f"\n[Ailleurs]({arg})\n"
    elif kind == "bare":
        lesson += f"\nVoir {arg}.\n"
    elif kind == "copy":
        lesson = with_section_text(lesson, "Explication", LONG_PASSAGE)
    elif kind == "no_mermaid":
        lesson = re.sub(r"```mermaid.*?```", "", lesson, flags=re.DOTALL)
    elif kind == "bad_mermaid":
        lesson = lesson.replace("flowchart TD", "pie title Chats")
    elif kind == "marker":
        lesson = with_section_text(lesson, "Explication", f"Un fait [{arg}].")
    elif kind == "essential":
        lesson = lesson.replace("- Les têtes sont concaténées puis projetées [1].\n", "")
    elif kind == "selftest":
        lesson = lesson.replace("5. Comment les têtes sont-elles combinées ?\n", "")
    elif kind == "title":
        lesson = lesson.replace(f"# {TITLE}", f"# {arg}", 1)
    elif kind == "extra_section":
        lesson += "\n## Bonus\n\nUn texte en plus.\n"
    elif kind == "swap":
        lesson = lesson.replace("## Prérequis", "## TMP").replace("## Objectifs", "## Prérequis")
        lesson = lesson.replace("## TMP", "## Objectifs")
    elif kind == "long_quote":
        quote = " ".join(f"mot{n}" for n in range(MAX_QUOTE_WORDS + 5))
        lesson = with_section_text(lesson, "Explication", f"Il écrit « {quote} » [1].")
    found = problems_of(lesson)
    assert any(problem in p for p in found), found


def test_code_blocks_are_not_counted_in_words() -> None:
    lesson = lesson_markdown(1500)
    code = "\n```python\n" + "x = 1\n" * 2000 + "```\n"
    result = check_lesson(
        with_section_text(lesson, "Explication", code), title=TITLE, sources=SOURCES
    )
    assert result.words == 1500 and result.problems == []


def test_short_attributed_quotation_is_not_a_copy() -> None:
    short = " ".join(SOURCE_ONE.split()[:20])
    quoted = with_section_text(lesson_markdown(1500), "Explication", f"« {short} » [1]")
    assert problems_of(quoted) == []


def test_long_copy_in_quotation_without_marker_is_a_copy() -> None:
    quoted = with_section_text(lesson_markdown(1500), "Explication", f"« {LONG_PASSAGE} »")
    assert any("recopié de la source [1]" in p for p in problems_of(quoted))


def test_copy_of_exactly_25_words_is_allowed() -> None:
    passage = " ".join(SOURCE_ONE.split()[:MAX_QUOTE_WORDS])
    assert problems_of(with_section_text(lesson_markdown(1500), "Explication", passage)) == []


def test_links_are_compared_loosely() -> None:
    sources = [(1, "https://Site0.exemple.org/article/", "Texte.")]
    lesson = lesson_markdown(1500).replace(
        "https://site0.exemple.org/article", "https://site0.EXEMPLE.org/article#haut"
    )
    found = check_lesson(lesson, title=TITLE, sources=sources).problems
    assert not any("Lien absent" in p and "site0" in p for p in found)


def test_headings_inside_code_blocks_are_ignored() -> None:
    fenced = with_section_text(lesson_markdown(1500), "Explication", "```\n## Faux titre\n```")
    assert problems_of(fenced) == []


def test_problems_are_in_french_and_never_empty_strings() -> None:
    found = problems_of("Du texte sans structure.")
    assert found and all(p.strip() for p in found)


@pytest.mark.parametrize(
    "raw",
    [
        "<pre>\nx",  # bloc HTML de type 1 jamais refermé : avalerait toute la suite au rendu
        "<script> charge un fichier.",
        "Un `List` de <String> en Java.",  # balise en ligne
        "<!-- note -->",
    ],
)
def test_raw_html_outside_code_is_refused(raw: str) -> None:
    lesson = with_section_text(lesson_markdown(1500), "Explication", raw)
    found = problems_of(lesson)
    assert any("HTML brut hors d'un bloc de code" in p for p in found), found


def test_review_reproduction_keeps_sections_seen_by_the_renderer() -> None:
    """Revue finale de la phase 4, I2 : le Vérificateur lit comme le rendu (`html: True`)."""
    found = problems_of("## Objectifs\n- a\n<pre>\nx\n## Explication\nLong texte important.\n")
    assert any("HTML brut" in p for p in found)
    assert any("Section manquante : « ## Explication »" in p for p in found)


def test_html_inside_code_is_accepted() -> None:
    code = "Écrire `<script>` ou :\n\n```html\n<pre>\n<script>x</script>\n```"
    assert problems_of(with_section_text(lesson_markdown(1500), "Explication", code)) == []
