"""Types communs de l'étude (5.2) : fiche et empreinte du recto."""

import pytest
from pydantic import ValidationError

from app.agents.tools.study_schema import CardDraft, card_hash


def test_card_hash_ignores_case_and_spaces() -> None:
    a = card_hash("Qu'est-ce qu'un  index ?")
    assert a == card_hash("  qu'est-ce QU'UN index ?\n")
    assert a != card_hash("Qu'est-ce qu'une clé ?")
    assert len(a) == 64


def test_card_draft_bounds() -> None:
    card = CardDraft(front="Qu'est-ce qu'un index ?", back="Une structure de recherche.")
    assert card.skill is None
    with pytest.raises(ValidationError):
        CardDraft(front="abc", back="x")
    with pytest.raises(ValidationError):
        CardDraft(front="Question valable ?", back="")
    with pytest.raises(ValidationError):
        CardDraft(front="x" * 301, back="x")


def test_card_back_is_shortened_not_refused() -> None:
    card = CardDraft(front="Question valable ?", back="mot " * 400)
    assert len(card.back) <= 600
