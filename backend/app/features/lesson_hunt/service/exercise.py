"""Composer un brouillon avec exactement deux changements localisés."""

from app.agents.tools.lesson_hunt_port import ErrorEdit, ErrorPair


def _span(markdown: str, edit: ErrorEdit) -> tuple[int, int, str]:
    start = markdown.find(edit.source)
    if start < 0 or markdown.find(edit.source, start + 1) >= 0:
        raise ValueError("Le passage doit apparaître une fois dans le chapitre.")
    return start, start + len(edit.source), edit.replacement


def apply_edits(markdown: str, pair: ErrorPair) -> str:
    first, second = sorted((_span(markdown, edit) for edit in pair.edits), key=lambda span: span[0])
    if first[1] > second[0]:
        raise ValueError("Les passages modifiés doivent être distincts.")
    return (
        markdown[: first[0]]
        + first[2]
        + markdown[first[1] : second[0]]
        + second[2]
        + markdown[second[1] :]
    )
