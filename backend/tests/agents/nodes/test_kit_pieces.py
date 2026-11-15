"""Contrôle de l'honnêteté des pièces du kit (D142) : fonctions pures de `honesty` et conventions
de contenu des schémas."""

from app.agents.nodes.tracker.honesty import (
    allowed_phrases,
    fix_answers,
    flagged_terms,
    length_problems,
    meta_words,
    retry_message,
    review,
)
from app.agents.tools.kit_schema import (
    Followups,
    FormAnswer,
    FormAnswers,
    Letter,
    LinkedInMessages,
    Pitch,
    join_parts,
)
from tests.agents.graphs.kit_support import filler, letter_text
from tests.support.kit import COMPANY, TITLE, default_context

CTX = default_context(contact="Jeanne Dupuis")


def test_allowed_phrases_are_whole_phrases_only() -> None:
    assert allowed_phrases(CTX) == [COMPANY, TITLE, "Jeanne Dupuis"]
    assert allowed_phrases(default_context()) == [COMPANY, TITLE]  # jamais les termes de l'offre


def test_company_title_and_contact_are_not_flagged() -> None:
    text = f"Bonjour Jeanne Dupuis, votre poste de {TITLE} chez {COMPANY} m'intéresse."
    assert flagged_terms(Letter(text=text), CTX) == []


def test_unsupported_terms_are_listed_once_in_order() -> None:
    draft = Followups(day_7="J'ai 5 ans sur Kubernetes.", day_14="Encore Kubernetes et 5 ans.")
    assert flagged_terms(draft, CTX) == ["5", "Kubernetes"]


def test_invitation_and_message_are_both_checked() -> None:
    draft = LinkedInMessages(invitation="Bonjour, 12 ans de Rust.", message=filler(20))
    assert set(flagged_terms(draft, CTX)) == {"12", "Rust"}


def test_length_bounds_per_piece() -> None:
    assert length_problems(Letter(text=letter_text(300))) == []
    assert length_problems(Letter(text=filler(249)))[0].startswith("le champ `text` fait 249 mots")
    assert "de 250 à 350 mots" in length_problems(Letter(text=filler(351)))[0]
    assert length_problems(Pitch(text=filler(130))) == []
    assert length_problems(Pitch(text=filler(171)))
    short = LinkedInMessages(invitation="Bonjour.", message=filler(151))
    assert "150 mots au plus" in length_problems(short)[0]
    two = Followups(day_7=filler(121), day_14=filler(120))
    assert [p.split("`")[1] for p in length_problems(two)] == ["day_7"]


def test_meta_words_is_a_number_or_one_count_per_part() -> None:
    assert meta_words(Letter(text=filler(10))) == 10
    assert meta_words(LinkedInMessages(invitation="Salut.", message=filler(7))) == 7
    assert meta_words(Followups(day_7=filler(3), day_14=filler(4))) == {"day_7": 3, "day_14": 4}
    assert meta_words(FormAnswers()) is None


def test_retry_message_names_terms_and_lengths() -> None:
    found = review(Letter(text=f"{filler(100)} 5 ans sur Kubernetes."), CTX)
    message = retry_message(found)
    assert message.startswith("N'écris rien qui ne soit pas dans le profil : 5, Kubernetes.")
    assert "Respecte les longueurs" in message and "de 250 à 350 mots" in message
    assert not review(Letter(text=letter_text(300)), CTX)


def test_form_answers_are_fixed_by_the_code() -> None:
    items = [
        FormAnswer(question="Prétentions salariales ?", answer="45 k€", fact_ids=["x1"]),
        FormAnswer(question="Permis ?", answer="Oui.", fact_ids=["x1", "zz9", "x1"]),
        FormAnswer(question="Disponibilité ?", answer="Immédiate.", fact_ids=[]),
        FormAnswer(question="Mobilité ?", answer="Partout.", fact_ids=["zz9"]),
    ]
    fixed = fix_answers(FormAnswers(items=items), {"x1", "c1"})
    assert [(i.answer, i.fact_ids, i.state) for i in fixed.items] == [
        ("", [], "salary"),
        ("Oui.", ["x1"], "ok"),
        ("", [], "to_complete"),
        ("", [], "to_complete"),
    ]
    assert fixed.parts() == {"answer_1": "", "answer_2": "Oui.", "answer_3": "", "answer_4": ""}
    rendered = fixed.render()
    assert "À remplir par toi" in rendered and rendered.count("À compléter") == 2


def test_english_salary_question_is_emptied_too() -> None:
    item = FormAnswer(question="What is your expected salary?", answer="60k", fact_ids=["x1"])
    assert fix_answers(FormAnswers(items=[item]), {"x1"}).items[0].state == "salary"


def test_join_parts_drops_separator_lines_of_the_texts() -> None:
    joined = join_parts("Premier\n---\nsuite", "Second")
    assert joined == "Premier\nsuite\n\n---\n\nSecond"
    assert [part.strip() for part in joined.split("\n\n---\n\n")] == ["Premier\nsuite", "Second"]
