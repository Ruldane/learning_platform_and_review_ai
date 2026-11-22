import re

from tests.agents.nodes.test_lesson_checks import problems_of, with_section_text
from tests.support.lessons import lesson_markdown


def test_mermaid_in_another_section_does_not_satisfy_diagrams() -> None:
    lesson = lesson_markdown()
    fenced = re.search(r"```mermaid.*?```", lesson, flags=re.DOTALL)
    assert fenced is not None
    moved = with_section_text(lesson.replace(fenced[0], ""), "Explication", fenced[0])
    assert any("dans « Schémas »" in problem for problem in problems_of(moved))


def test_french_python_identifiers_and_comments_are_reported() -> None:
    code = """```python
def normalize_response(réponse):
    # Cette fonction retourne la valeur
    return réponse.strip()
```"""
    draft = with_section_text(lesson_markdown(), "Exemple travaillé", code)
    problems = problems_of(draft)
    assert any("identifiant" in problem and "réponse" in problem for problem in problems)
    assert any("commentaire" in problem for problem in problems)


def test_french_sample_values_in_english_python_code_are_allowed() -> None:
    code = """```python
# Normalize the sample value
answer = "Cette fonction retourne la valeur"
title = "Une réponse"
```"""
    draft = with_section_text(lesson_markdown(), "Exemple travaillé", code)
    assert problems_of(draft) == []
