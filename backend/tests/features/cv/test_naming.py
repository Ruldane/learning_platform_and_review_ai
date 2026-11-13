"""Nom du fichier d'un CV (6.2)."""

from app.features.cv.service.naming import cv_filename


def test_cv_filename() -> None:
    assert (
        cv_filename("Camille Exemple", "Société Fictive", "AI Product Engineer")
        == "CV_Camille_Exemple_Societe_Fictive_AI_Product_Engineer.pdf"
    )


def test_cv_filename_never_empty() -> None:
    assert cv_filename("   ", None, None) == "CV.pdf"
    assert cv_filename("", "", "!!!") == "CV.pdf"


def test_cv_filename_drops_odd_characters_and_empty_parts() -> None:
    assert (
        cv_filename("Zoé L'Exemple", None, "Dev C++ / IA (H/F)")
        == "CV_Zoe_LExemple_Dev_C_IA_HF.pdf"
    )
    assert cv_filename("Jean-Émile", "Ça & Co", None) == "CV_Jean-Emile_Ca_Co.pdf"


def test_cv_filename_expands_ligatures_and_drops_lone_dashes() -> None:
    assert (
        cv_filename("Cœur Sœur", "L'Œil SAS", "Dev - IA – Strauß")
        == "CV_Coeur_Soeur_LOeil_SAS_Dev_IA_Strauss.pdf"
    )


def test_cv_filename_parts_are_at_most_forty_characters() -> None:
    name = cv_filename("Camille", None, "Ingénieure " * 10)
    title = name.removeprefix("CV_Camille_").removesuffix(".pdf")
    assert len(title) <= 40 and not title.endswith("_")
    assert name.isascii()
