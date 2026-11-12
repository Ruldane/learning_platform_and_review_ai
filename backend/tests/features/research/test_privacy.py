import pytest

from app.features.research.service.privacy import Identity, scrub_query

ME = Identity("Jane Doé", "jane.doe@mail.fr")


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("cours rag jane.doe@mail.fr", "cours rag"),
        ("Jane Doe portfolio data", "portfolio data"),
        ("doé formation llm", "formation llm"),  # nom de famille, accents ignorés
        ("DOE formation llm", "formation llm"),
        ("Jane python", "Jane python"),  # prénom seul gardé
        ("appeler 06 12 34 56 78 ou +33 6 12 34 56 78", "appeler ou"),
        ("rag 2024 llama 3.1 8b", "rag 2024 llama 3.1 8b"),  # chiffres ordinaires gardés
        ("0612345678 et 06.12.34.56.78 et 06-12-34-56-78", "et et"),
        ("tel +1 (415) 555-0100 urgent", "tel urgent"),
        ("0033 6 12 34 56 78 stage", "stage"),
        ("écrire à autre.personne@exemple.com stage", "écrire à stage"),
        ("python 3.12 sortie 2023 12 31", "python 3.12 sortie 2023 12 31"),
        ("doe-reader library", "doe-reader library"),
        ("doesnt matter", "doesnt matter"),
        ("   espaces    multiples   ", "espaces multiples"),
        ("", ""),
    ],
)
def test_scrub_query(raw: str, clean: str) -> None:
    assert scrub_query(raw, ME) == clean


def test_decomposed_accent_goes_with_its_letter() -> None:
    assert scrub_query("avis de doé hier", Identity("Jane Doé", None)) == "avis de hier"


def test_family_name_shorter_than_three_letters_is_kept_but_full_name_goes() -> None:
    identity = Identity("Anne Li", None)
    assert scrub_query("li ion batterie", identity) == "li ion batterie"
    assert scrub_query("Anne Li ion", identity) == "ion"


def test_particles_and_hyphens_in_names() -> None:
    identity = Identity("Jean de La Fontaine", None)
    assert scrub_query("fables fontaine jean", identity) == "fables jean"
    assert scrub_query("jean de la fontaine fables", identity) == "fables"
    assert scrub_query("Marie Dupont-Martin cv", Identity("Marie Dupont-Martin", None)) == "cv"


def test_single_word_name_is_kept_like_a_first_name() -> None:
    assert scrub_query("jane python", Identity("Jane", None)) == "jane python"


def test_no_identity_still_removes_emails_and_phones() -> None:
    assert scrub_query("a@b.fr 06 12 34 56 78 cours", Identity(None, None)) == "cours"
