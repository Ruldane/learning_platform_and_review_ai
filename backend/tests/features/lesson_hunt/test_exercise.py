import pytest

from app.agents.tools.lesson_hunt_port import ErrorEdit, ErrorPair
from app.features.lesson_hunt.service.exercise import apply_edits


def _edit(source: str, replacement: str) -> ErrorEdit:
    return ErrorEdit(
        source=source,
        replacement=replacement,
        explanation="La correction découle du principe expliqué dans le chapitre.",
    )


def test_two_edits_replace_only_their_source_fragments() -> None:
    markdown = "# Collections\n\nUn tuple est immuable.\nUn ensemble élimine les doublons."
    edits = ErrorPair(
        edits=[
            _edit("Un tuple est immuable.", "Un tuple est modifiable."),
            _edit("Un ensemble élimine les doublons.", "Un ensemble conserve les doublons."),
        ]
    )

    assert apply_edits(markdown, edits) == (
        "# Collections\n\nUn tuple est modifiable.\nUn ensemble conserve les doublons."
    )


def test_ambiguous_or_overlapping_sources_are_rejected() -> None:
    markdown = "Un tuple est immuable. Un tuple est immuable. Un ensemble contient des valeurs."
    edits = ErrorPair(
        edits=[
            _edit("Un tuple est immuable.", "Un tuple contient un état modifiable."),
            _edit("Un ensemble contient des valeurs.", "Un ensemble conserve tous les doublons."),
        ]
    )
    with pytest.raises(ValueError):
        apply_edits(markdown, edits)

    edits = ErrorPair(
        edits=[
            _edit("Un ensemble contient des valeurs.", "Un ensemble contient des doublons."),
            _edit("ensemble contient des valeurs.", "ensemble préserve tous les doublons."),
        ]
    )
    with pytest.raises(ValueError):
        apply_edits(markdown, edits)
