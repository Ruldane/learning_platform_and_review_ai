"""Règles du Maquettiste (D125) : textes recopiés tels quels (forme seule normalisée), retrait des
textes inventés, images comparées page à page, question `cv_template` et analyse de la réponse."""

import pytest

from app.agents.nodes.designer import compared
from app.agents.nodes.designer_steps import (
    MAX_ADJUSTMENTS,
    DesignAnswer,
    invented_lines,
    parse_answer,
    plain,
    question,
    verbatim,
)
from app.agents.tools.cv_schema import CvContent
from tests.support.cv_templates import sample_dict
from tests.support.profile import CV_TEXT


def sample(**over: object) -> CvContent:
    return CvContent.model_validate(sample_dict(**over))


def test_plain_only_changes_form() -> None:
    assert plain("Développeuse IA — Atelier\n  Fictif") == plain("développeuse ia - atelier fictif")
    assert plain("ﬁchier l’outil") == "fichier l'outil"
    assert plain("cinq ans") != plain("5 ans")


def test_copied_lines_pass_even_when_wrapped_in_the_pdf() -> None:
    assert invented_lines(sample(), CV_TEXT) == []


def test_invented_and_reworded_lines_are_found() -> None:
    sections = sample_dict()["sections"]
    sections[1]["entries"][0]["lines"] += [
        {"text": "Réduit de 45 % le temps de traitement"},  # chiffre changé
        {"text": "Conçu un assistant interne avec LangGraph pour le support"},  # recopié
    ]
    sections.append({"key": "skills", "title": "Savoir-faire", "items": [{"text": "Python"}]})
    content = sample(sections=sections, headline="Experte IA")
    assert invented_lines(content, CV_TEXT) == [
        "Experte IA",
        "Réduit de 45 % le temps de traitement",
        "Savoir-faire",
    ]


def test_verbatim_removes_invented_texts_and_empty_parts() -> None:
    sections = sample_dict()["sections"]
    sections[1]["entries"][0]["lines"] = [{"text": "Inventé", "fact_ids": ["x1a1"]}]
    sections[1]["entries"][0]["heading"] = "Poste inventé"
    sections[1]["entries"][0]["dates"] = "1999"
    sections.append({"key": "skills", "title": "Inventé", "items": [{"text": "Python"}]})
    content = sample(sections=sections, headline="Inventé", contact=["camille@x", "Lyon"])
    kept = verbatim(content, invented_lines(content, CV_TEXT))
    assert kept.headline is None and kept.contact == ["Lyon"]
    assert [s.key for s in kept.sections] == ["summary", "languages"]  # vidée ou titre inventé
    assert all(not line.fact_ids for s in kept.sections for line in s.items)


def test_compared_interleaves_original_and_render_within_the_limit() -> None:
    legend, images = compared([b"o1", b"o2", b"o3"], [b"r1", b"r2", b"r3", b"r4"])
    assert images == [b"o1", b"r1", b"o2", b"r2"]
    assert legend == (
        "Images, in order: original, page 1; rendu, page 1; original, page 2; rendu, page 2."
    )
    assert compared([b"o1"], [b"r1", b"r2"])[1] == [b"o1", b"r1", b"r2"]


def test_question_offers_three_options_then_two_at_the_cap() -> None:
    ask = question(87, 0)
    assert ask["question"] == "The template matches your CV at 87%. Do you approve it?"
    assert [o["value"] for o in ask["options"]] == ["validate", "adjust", "restart"]
    assert [o["label"] for o in ask["options"]] == ["Approve", "Adjust", "Restart the capture"]
    assert ask["fields"] == [{"id": "instruction", "label": "What to change", "max_length": 500}]
    capped = question(70, MAX_ADJUSTMENTS)
    assert [o["value"] for o in capped["options"]] == ["validate", "restart"]
    assert capped["fields"] == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("validate", DesignAnswer(action="validate")),
        ("restart", DesignAnswer(action="restart")),
        ({"action": "validate", "instruction": "ignorée"}, DesignAnswer(action="validate")),
        (
            {"answers": {"instruction": " Plus d'air "}},
            DesignAnswer(action="adjust", instruction="Plus d'air"),
        ),
        (
            {"action": "adjust", "instruction": "x" * 900},
            DesignAnswer(action="adjust", instruction="x" * 500),
        ),
        ("adjust", None),  # consigne requise
        ({"answers": {"instruction": "   "}}, None),
        ({"answers": {"autre": "x"}}, None),
        ({"action": "supprimer"}, None),
        (42, None),
    ],
)
def test_parse_answer(value: object, expected: DesignAnswer | None) -> None:
    assert parse_answer(value, 0) == expected


def test_no_adjustment_beyond_the_fifth() -> None:
    assert parse_answer({"answers": {"instruction": "Encore"}}, MAX_ADJUSTMENTS) is None
    assert parse_answer("validate", MAX_ADJUSTMENTS) == DesignAnswer(action="validate")
