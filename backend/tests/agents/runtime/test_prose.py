"""Texte libre trop long : raccourci, jamais refusé (GLM dépasse les plafonds, D97)."""

import logging

import pytest
from pydantic import BaseModel, Field, ValidationError

from app.agents.runtime.prose import Prose, shorten


class Note(BaseModel):
    summary: Prose = Field(min_length=5, max_length=40)


def test_shorten_keeps_a_text_within_the_limit() -> None:
    assert shorten("Court.", 40) == "Court."
    assert shorten("x" * 40, 40) == "x" * 40


def test_shorten_cuts_at_the_last_sentence_end_when_it_keeps_most_of_the_text() -> None:
    text = "Premier point clair. Second point net. Troisième point bien trop long ici."
    assert shorten(text, 50) == "Premier point clair. Second point net."


def test_shorten_cuts_between_words_with_an_ellipsis_otherwise() -> None:
    text = "Une seule phrase très longue qui ne finit jamais avant la limite fixée"
    cut = shorten(text, 30)
    assert cut == "Une seule phrase très longue…"
    assert len(cut) <= 30


def test_shorten_cuts_a_text_without_spaces() -> None:
    assert shorten("a" * 50, 10) == "a" * 9 + "…"


def test_prose_field_shortens_instead_of_refusing() -> None:
    text = "Un résumé neutre du tour, bien trop long pour la limite."
    note = Note.model_validate({"summary": text})
    assert len(note.summary) <= 40
    assert note.summary.endswith("…")


def test_prose_field_logs_the_lengths_only(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app")
    Note.model_validate({"summary": "secretvaleur " * 10})
    assert "summary" in caplog.text and "130" in caplog.text and "40" in caplog.text
    assert "secretvaleur" not in caplog.text


def test_prose_field_keeps_the_other_constraints_and_the_schema() -> None:
    with pytest.raises(ValidationError):
        Note.model_validate({"summary": "abc"})
    with pytest.raises(ValidationError):
        Note.model_validate({"summary": 12})
    schema = Note.model_json_schema()["properties"]["summary"]
    assert schema["maxLength"] == 40 and schema["minLength"] == 5


def test_prose_without_a_max_length_is_refused_at_class_creation() -> None:
    with pytest.raises(TypeError):

        class Unbounded(BaseModel):
            text: Prose
