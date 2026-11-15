"""Contrôle des faits d'un texte écrit au nom de January (7.1, critère 18.3) : un chiffre, un
outil, un titre ou un nom propre que le profil ne dit pas est rendu, par le code."""

from app.agents.tools.cv_schema import Link, SourcedLine
from app.agents.tools.text_claims import Claim, text_claims
from tests.support.cv_review import profile

LETTER_PROFILE = profile(
    line="Réduit de 30 % le temps de traitement avec Python",
    role="AI Engineer",
    skills=["Python", "Docker"],
)


def terms(text: str, **kw: object) -> list[str]:
    return [c.term for c in text_claims(text, LETTER_PROFILE, **kw)]  # type: ignore[arg-type]


def test_text_claims_number_and_tool() -> None:
    claims = text_claims("Avec 5 ans d'expérience sur Kubernetes, je…", profile(skills=["Docker"]))
    assert {c.term for c in claims} >= {"5", "Kubernetes"}
    assert Claim("number", "5") in claims and Claim("tool", "Kubernetes") in claims


def test_text_claims_accepts_profile_facts() -> None:
    text = (
        "Chez Société Fictive, j'ai réduit de 30% le temps de traitement avec Python et Docker."
        " Camille Exemple"
    )
    assert text_claims(text, LETTER_PROFILE) == []


def test_text_claims_accepts_dates_links_and_identity_of_the_profile() -> None:
    p = profile(
        links=[Link(label="GitHub", url="https://github.com/camille-exemple")],
        title=SourcedLine(text="Développeuse IA", sources=["cv"]),
    )
    p.identity.phone = "06 12 34 56 78"
    p.experiences[0].start = "2019-03"
    text = "Depuis 2019, voir GitHub. Appelez-moi au 06 12 34 56 78."
    assert text_claims(text, p) == []


def test_text_claims_allowed_posting_title() -> None:
    text = "Je candidate à votre poste de Lead Data chez Exemple Tech."
    assert text_claims(text, LETTER_PROFILE, allowed=["Lead Data", "Exemple Tech"]) == []
    assert "Lead" in terms(text)


def test_text_claims_title_claimed() -> None:
    claims = text_claims("J'ai travaillé en tant que Lead Data.", LETTER_PROFILE)
    assert Claim("title", "Lead") in claims


def test_text_claims_title_of_the_profile_is_fine() -> None:
    p = profile(role="Senior AI Engineer")
    assert text_claims("Je suis Senior AI Engineer depuis longtemps.", p) == []


def test_posting_number_is_not_a_fact_of_january() -> None:
    claims = text_claims(
        "Vous demandez 3 ans d'expérience.", LETTER_PROFILE, allowed=["Exemple Tech"]
    )
    assert Claim("number", "3") in claims


def test_number_words_and_percent_are_read_like_the_validator() -> None:
    assert terms("J'ai deux ans d'expérience.") == ["deux"]
    assert terms("J'ai réduit de quarante pour cent les coûts.") == ["quarante"]
    assert terms("Un gain de 12 000 € et de 45 %.") == ["12000", "45%"]
    assert terms("Soit 1 000 utilisateurs.") == ["1000"]


def test_unknown_proper_name_is_claimed_unless_allowed() -> None:
    text = "J'ai découvert votre produit chez Acme Corp et sur LinkedIn."
    assert terms(text) == ["Acme", "Corp", "LinkedIn"]
    assert terms(text, allowed=["Acme Corp"]) == ["LinkedIn"]


def test_greetings_and_sentence_starts_are_not_names() -> None:
    text = (
        "Bonjour Madame, Monsieur,\nJe vous écris pour votre offre. Cordialement,\nCamille Exemple"
    )
    assert text_claims(text, LETTER_PROFILE) == []


def test_ambiguous_word_is_a_tool_only_in_its_product_form() -> None:
    assert terms("J'ai une vue d'ensemble du projet.") == []
    assert terms("Je maîtrise Vue.js au quotidien.") == ["Vue"]


def test_claims_are_in_text_order_without_duplicates() -> None:
    text = "Kubernetes pendant 5 ans, puis Terraform. Encore 5 ans de Kubernetes."
    assert terms(text) == ["Kubernetes", "5", "Terraform"]


def test_tool_written_as_several_words_keeps_the_text_form() -> None:
    assert terms("Mes pipelines Scikit-learn en production.") == ["Scikit-learn"]


def test_empty_text_and_empty_profile_claim_nothing() -> None:
    assert text_claims("", LETTER_PROFILE) == []
    assert text_claims("   \n", LETTER_PROFILE) == []
