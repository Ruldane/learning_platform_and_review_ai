"""`lesson_terms`: common teaching words, in English or French, point to no chapter."""

from app.features.lessons.service.conversation import lesson_terms


def test_english_filler_words_are_dropped() -> None:
    assert lesson_terms("Can you explain how the gradient descent works?") == [
        "gradient",
        "descent",
        "works",
    ]


def test_french_filler_words_are_still_dropped() -> None:
    assert lesson_terms("Peux-tu expliquer la descente de gradient ?") == [
        "expliquer",
        "descente",
        "gradient",
    ]
