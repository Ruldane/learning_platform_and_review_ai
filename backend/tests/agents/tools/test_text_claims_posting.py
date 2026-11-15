"""Contrôle des faits d'un texte (7.1) : expressions citées de l'offre (`allowed`), titres que le
texte se donne, noms propres, formules d'appel et dates."""

from app.agents.tools.cv_schema import SourcedLine
from app.agents.tools.text_claims import Claim, text_claims
from app.agents.tools.text_claims_names import ACRONYMS
from tests.support.cv_review import profile
from tests.support.text_claims import COMPANY, TITLE, P, terms

# --- allowed : des expressions citées, jamais un moyen de se donner l'offre ---


def test_cited_company_and_posting_title_are_fine() -> None:
    text = "Je candidate à votre poste de Lead Data chez Exemple Tech."
    assert terms(text, allowed=("Lead Data", "Exemple Tech")) == []
    assert "Lead" in terms(text)
    text = "Votre offre de Lead Data Engineer (H/F) m'intéresse."
    assert terms(text, allowed=("Lead Data Engineer (H/F)",)) == []


def test_posting_title_claimed_as_own_is_flagged_even_if_allowed() -> None:
    text = f"En tant que {TITLE} chez {COMPANY}, j'ai piloté Kubernetes et Terraform."
    claims = text_claims(text, P, allowed=(COMPANY, TITLE))
    assert Claim("title", "Lead") in claims
    assert Claim("tool", "Kubernetes") in claims and Claim("tool", "Terraform") in claims
    assert Claim("name", "Société") not in claims  # « chez » cite l'entreprise
    assert terms("En tant que Lead Data, je…", allowed=("Lead Data",)) == ["Lead", "Data"]


ALLOWED = (COMPANY, TITLE, "Julie Martin")


def test_title_of_the_posting_is_flagged_when_the_text_claims_it() -> None:
    """Chaque phrase se donne l'intitulé de l'offre : `allowed` ne le retire pas."""
    for text in (
        "Je travaille avec Python en tant que Lead Data Engineer.",
        "J'ai envie de rejoindre Société Fictive en tant que Lead Data Engineer.",
        "Pour Société Fictive je suis Lead Data Engineer.",
        "Fort de mon expérience de Lead Data Engineer, je livre en Python.",
        "Lead Data Engineer depuis 2021, je pilote Python.",
        "Dans mon poste actuel de Lead Data Engineer, j'ai livré.",
        "Mon parcours de Lead Data Engineer chez Société Fictive.",
        "J'étais Lead Data Engineer.",
        "Ayant été lead data engineer, je…",
    ):
        claims = text_claims(text, P, allowed=ALLOWED)
        assert claims, text
        assert not {c.term for c in claims} <= {"Société", "Fictive"}, text


def test_posting_title_with_a_tool_is_flagged_as_own() -> None:
    claims = text_claims(
        "J'ai travaillé pour Société Fictive comme Senior Data Engineer AWS.",
        P,
        allowed=(COMPANY, "Senior Data Engineer AWS"),
    )
    assert Claim("title", "Senior") in claims and Claim("tool", "AWS") in claims


def test_posting_title_is_cited_only_as_the_offer_of_the_other() -> None:
    for text in (
        "Votre poste de Lead Data Engineer m'intéresse.",
        "Je candidate à votre poste de Lead Data Engineer chez Société Fictive.",
        "Votre offre de Lead Data Engineer (H/F) m'intéresse beaucoup.",
        "Je réponds à cette offre de Lead Data Engineer.",
        "I am applying for the Lead Data Engineer role.",
        "I am excited by your Lead Data Engineer position.",
    ):
        assert text_claims(text, P, allowed=ALLOWED) == [], text


def test_lowercase_titles_after_a_self_attribution_are_flagged() -> None:
    for text in (
        "J'étais lead developer.",
        "Ayant été lead developer, je…",
        "J'ai occupé le poste de lead developer.",
        "J'ai exercé comme directeur technique.",
        "Étant responsable produit, je…",
        "Mon rôle de lead developer m'a appris.",
        "I worked as senior engineer.",
        "I served as principal engineer.",
        "Working as staff engineer, I…",
        "My experience as head of data.",
    ):
        assert any(c.kind == "title" for c in text_claims(text, P)), text


def test_posting_stack_claimed_as_own_is_flagged() -> None:
    claims = text_claims(
        "Experte Kubernetes, j'ai déployé Spark sur AWS.", P, allowed=(COMPANY, TITLE)
    )
    assert {Claim("tool", "Kubernetes"), Claim("tool", "Spark"), Claim("tool", "AWS")} <= set(
        claims
    )


# --- les titres : seulement ceux que le texte se donne ---


def test_text_claims_title_claimed() -> None:
    assert Claim("title", "Lead") in text_claims("J'ai travaillé en tant que Lead Data.", P)
    assert Claim("title", "Senior") in text_claims("As a Senior engineer, I led...", P)
    assert terms("Je suis Lead à la maison.") == ["Lead"]


def test_title_of_the_profile_is_fine() -> None:
    p = profile(role="Senior AI Engineer")
    assert text_claims("Je suis Senior AI Engineer depuis longtemps.", p) == []


def test_title_word_outside_a_self_attribution_is_not_flagged() -> None:
    assert terms("Responsable de la mise en production de modèles.") == []
    assert terms("Je me réjouis de rencontrer le manager et le lead de l'équipe.") == []
    assert terms("Je vous remercie, en tant que candidate. Le lead…") == []


def test_title_of_the_profile_headline_is_fine() -> None:
    p = profile(title=SourcedLine(text="Lead Data Engineer", sources=["cv"]))
    assert text_claims("Je suis Lead Data Engineer.", p) == []


# --- les noms propres ---


def test_unknown_proper_name_is_claimed_unless_allowed() -> None:
    text = "J'ai découvert votre produit chez Acme Corp et sur LinkedIn."
    assert terms(text) == ["Acme", "Corp", "LinkedIn"]
    assert terms(text, allowed=("Acme Corp",)) == ["LinkedIn"]


def test_employer_names_at_sentence_start_or_in_capitals_are_claimed() -> None:
    assert terms("Capgemini m'a confié la refonte du portail.") == ["Capgemini"]
    assert terms("Merci.\nAccenture m'a appris la rigueur.") == ["Accenture"]
    assert terms("J'ai travaillé chez IBM et chez BNP.") == ["IBM", "BNP"]
    assert terms("Chez Acme, j'ai progressé.") == ["Acme"]
    assert terms("I joined Initech in 2024.") == ["Initech"]


def test_common_acronyms_are_not_names() -> None:
    assert terms("Mon CV, l'IA, les RH et un CDI en PME.") == []
    assert terms("Mon expérience chez GOOGLE.") == ["GOOGLE"]
    assert "CV" in ACRONYMS and "IBM" not in ACRONYMS and len(ACRONYMS) <= 20


def test_greetings_recipients_and_sentence_starts_are_not_names() -> None:
    text = (
        "Bonjour Madame, Monsieur,\nJe vous écris pour votre offre. Cordialement,\nCamille Exemple"
    )
    assert text_claims(text, P) == []
    assert terms("Bonjour Julie,\nVotre offre m'intéresse.") == []
    assert terms("Hello Julie Martin,\nThank you.") == []
    assert terms("Dear Hiring Manager,\nTeam, hello. Équipe") == []
    assert terms("Cela m'a permis de progresser. Elle m'a aidée.") == []


def test_contact_name_in_allowed_is_not_a_claim() -> None:
    assert terms("Échange avec Julie Martin.") == ["Julie", "Martin"]
    assert terms("Échange avec Julie Martin.", allowed=("Julie Martin",)) == []


def test_salutation_skips_only_its_own_line() -> None:
    """Le premier mot du corps de la lettre, après la formule d'appel, est lu."""
    assert terms("Madame, Monsieur,\nAccenture m'a appris la rigueur.") == ["Accenture"]
    assert terms("Madame,\nIBM m'a confié la refonte.") == ["IBM"]
    assert terms("Bonjour,\n\nGoogle m'a recrutée.") == ["Google"]
    assert terms("Cher Monsieur,\nChez Google, j'ai livré.") == ["Google"]
    assert terms("Bonjour Madame Martin,\nGoogle m'a recrutée.") == ["Google"]
    assert terms("Dear Sir,\nGoogle hired me.") == ["Google"]
    assert terms("Bonjour Madame Martin, merci.") == []


def test_a_month_next_to_a_count_is_not_a_date() -> None:
    assert terms("Depuis septembre 12 projets ont été livrés.") == ["12"]
    assert terms("In May 3 of my projects shipped.") == ["3"]
    assert terms("Since March 5 clients signed.") == ["5"]
    assert terms("My team of 4 may grow.") == ["4"]
    assert terms("J'ai commencé le 5 mars puis le 12 mai.") == []
    assert terms("I started on March 5, then on May 12th and on June 3.") == []
