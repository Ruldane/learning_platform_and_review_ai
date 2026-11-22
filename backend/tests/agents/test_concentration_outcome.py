"""Seule une évaluation explicite du Tuteur devient un repère."""

from app.agents.nodes.concentration import training_outcome


def test_extracts_a_training_mark_and_keeps_the_readable_reply() -> None:
    assert training_outcome("Bien expliqué.\n\n<!-- concentration:correct -->") == (
        "Bien expliqué.",
        "correct",
    )
    assert training_outcome("Revois la condition.\n<!-- concentration:retry -->\n") == (
        "Revois la condition.",
        "retry",
    )


def test_missing_or_invalid_mark_is_unknown() -> None:
    for answer in (
        "Quel sujet veux-tu réviser ?",
        "Texte <!-- concentration:correct -->",
        "<!-- concentration:retry -->",
        "Ceci est une note.\n<!-- concentration:other -->",
    ):
        assert training_outcome(answer) == (answer, None)
