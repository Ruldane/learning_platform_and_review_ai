"""Contrôle des faits d'un texte écrit au nom de January (7.1, critère 18.3) : chiffres, outils,
proportions. Le sens dangereux est le faux négatif : chaque test « invente » une phrase que le
profil ne dit pas."""

from app.agents.tools.text_claims import Claim, text_claims
from tests.support.cv_review import profile
from tests.support.text_claims import COMPANY, P, terms

# --- les chiffres : le texte des faits et les années, jamais un mois ni un contact ---


def test_text_claims_number_and_tool() -> None:
    claims = text_claims("Avec 5 ans d'expérience sur Kubernetes, je…", profile(skills=["Docker"]))
    assert {c.term for c in claims} >= {"5", "Kubernetes"}
    assert Claim("number", "5") in claims and Claim("tool", "Kubernetes") in claims


def test_text_claims_accepts_profile_facts() -> None:
    text = (
        "Chez Société Fictive, j'ai réduit de 30% le temps de traitement avec Python et Docker."
        " Camille Exemple"
    )
    assert text_claims(text, P) == []


def test_month_digits_of_the_dates_do_not_back_a_number() -> None:
    assert terms("Forte de 3 ans d'expérience en Python.") == ["3"]  # « 2021-03 »
    assert terms("J'ai 9 ans d'expérience.") == ["9"]  # « 2024-09 », « 2015-09 »
    assert terms("J'ai mené 12 projets.") == ["12"]  # le téléphone se termine par « 12 »
    assert terms("Je pilote une équipe de 6 développeurs.") == ["6"]  # « 06 »


def test_years_of_the_profile_dates_back_a_year() -> None:
    assert terms("Je développe en Python depuis 2015.") == []
    assert terms("Je développe en Python depuis 2012.") == ["2012"]


def test_own_contacts_in_the_signature_are_not_numbers() -> None:
    signature = "Cordialement,\nCamille Exemple\n06 12 34 56 78\ncamille.exemple@example.org\n"
    assert terms(signature + "https://github.com/camille-exemple") == []
    assert terms("Joignable au 06.12.34.56.78 ou sur github.com/camille-exemple") == []
    assert terms("Joignable au 07 12 34 56 78") != []  # un autre numéro n'est pas le sien


def test_posting_number_is_not_a_fact_of_january() -> None:
    assert terms("Vous demandez 3 ans d'expérience.", allowed=("Exemple Tech",)) == ["3"]


def test_a_number_inside_allowed_never_backs_a_number() -> None:
    allowed = ("Développeur Python 3 ans d'expérience", "Data Engineer 5+ ans")
    assert terms("J'ai 3 ans d'expérience.", allowed=allowed) == ["3"]
    assert terms("J'ai 5 ans d'expérience.", allowed=allowed) == ["5"]


def test_number_words_and_percent_are_read_like_the_validator() -> None:
    assert terms("J'ai deux ans d'expérience.") == ["deux"]
    assert terms("J'ai réduit de quarante pour cent les coûts.") == ["quarante"]
    assert terms("Un gain de 12 000 € et de 45 %.") == ["12000", "45%"]
    assert terms("Soit 1 000 utilisateurs.") == ["1000"]


def test_a_day_and_month_is_not_a_number_but_a_year_is_checked() -> None:
    assert terms("Je suis disponible pour un échange le 12 novembre.") == []
    assert terms("Notre échange du 3 mars, le 14/11/2021 ou on November 12th.") == []
    assert terms("Disponible à partir de janvier 2025.") == ["2025"]
    assert terms("Embauchée en 2024.") == []  # une fin d'expérience


def test_ratio_words_are_checked_like_the_cv_validator() -> None:
    assert terms("J'ai doublé le chiffre d'affaires.") == ["doublé"]
    assert terms("Des coûts baissés de moitié.") == ["moitié"]
    assert terms("Un gain x3 sur les délais.") == ["x3"]
    assert terms("Un gain de 3x sur les délais.") == ["3", "3x"]
    backed = profile(line="Doublé le volume de dossiers traités")
    assert text_claims("J'ai doublé le volume.", backed) == []


# --- les outils : le lexique, sans casse ---


def test_tool_is_read_without_case_against_the_profile() -> None:
    assert terms("Je travaille avec DOCKER et python.") == []
    assert terms("Je travaille avec KUBERNETES.") == ["KUBERNETES"]


def test_ambiguous_word_is_a_tool_only_in_its_product_form() -> None:
    assert terms("J'ai une vue d'ensemble du projet.") == []
    assert terms("Je maîtrise Vue.js au quotidien.") == ["Vue"]


def test_tool_written_as_several_words_keeps_the_text_form() -> None:
    assert terms("Mes pipelines Scikit-learn en production.") == ["Scikit-learn"]


# --- une lettre honnête, en français et en anglais, ne signale rien ---

FRENCH_LETTER = """Madame, Monsieur,

Votre offre de Développeuse IA chez Société Fictive a retenu mon attention. J'ai réduit de 30 % le
temps de traitement avec Python et Docker, et je maîtrise le machine learning.
Je suis disponible pour un échange le 12 novembre.

Cordialement,
Camille Exemple
06 12 34 56 78
"""
ENGLISH_LETTER = """Dear Hiring Manager,

I am applying for the Data Engineer position at Exemple Tech. At Exemple Tech I would use my
Python and Docker skills.

Best regards,
Camille Exemple
"""


def test_honest_letters_claim_nothing() -> None:
    assert terms(FRENCH_LETTER, allowed=(COMPANY, "Développeuse IA")) == []
    assert terms(ENGLISH_LETTER, allowed=("Exemple Tech", "Data Engineer")) == []


def test_dishonest_letter_names_each_invented_fact() -> None:
    letter = FRENCH_LETTER + "J'ai 5 ans d'expérience, je suis expert Kubernetes chez Capgemini."
    assert terms(letter, allowed=(COMPANY, "Développeuse IA")) == ["5", "Kubernetes", "Capgemini"]


def test_claims_are_in_text_order_without_duplicates() -> None:
    text = "Kubernetes pendant 5 ans, puis Terraform. Encore 5 ans de Kubernetes."
    assert terms(text) == ["Kubernetes", "5", "Terraform"]


def test_empty_text_and_empty_profile_claim_nothing() -> None:
    assert text_claims("", P) == []
    assert text_claims("   \n", P) == []
