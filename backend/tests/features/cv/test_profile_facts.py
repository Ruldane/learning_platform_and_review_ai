"""Un fait confirmé en revue entre au profil maître (I-2, re-revue de la vague de corrections) :
une langue s'écrit « Nom — niveau », un lien « Libellé — URL » ; ni l'un ni l'autre ne finit
dans le nom ou le libellé. Une URL invalide est refusée par le 422 habituel."""

import pytest

from app.agents.tools.cv_schema import (
    Education,
    Experience,
    Identity,
    Language,
    Link,
    MasterProfileData,
    assign_fact_ids,
    facts_of,
)
from app.core.errors import AppError
from app.features.cv.service.profile_facts import with_fact


def data() -> MasterProfileData:
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            languages=[Language(name="Anglais", level="B2", sources=["cv"])],
            links=[Link(label="GitHub", url="https://github.com/camille", sources=["cv"])],
        )
    )


def test_a_confirmed_language_rewrite_writes_the_name_and_the_level() -> None:
    out = with_fact(data(), "l1", "Anglais — C1")
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais", "C1")
    assert facts_of(out)["l1"] == "Anglais — C1"
    assert "january" in out.languages[0].sources


@pytest.mark.parametrize(
    "text", ["Anglais (C1)", "Anglais - C1", "Anglais : C1", "Anglais – C1", "Anglais — C1"]
)
def test_a_language_written_with_another_separator_still_splits(text: str) -> None:
    out = with_fact(data(), "l1", text)
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais", "C1")
    assert facts_of(out)["l1"] == "Anglais — C1"


def test_a_language_text_without_separator_clears_the_old_level() -> None:
    out = with_fact(data(), "l1", "Anglais courant")
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais courant", None)
    assert facts_of(out)["l1"] == "Anglais courant"  # jamais le niveau B2 à côté du texte neuf


def test_a_malformed_url_is_refused_not_a_crash() -> None:
    with pytest.raises(AppError) as err:
        with_fact(data(), "k1", "GitHub — http://[::1")
    assert err.value.status_code == 422


def test_a_confirmed_link_rewrite_writes_the_label_and_the_url() -> None:
    out = with_fact(data(), "k1", "GitHub — https://github.com/autre")
    assert (out.links[0].label, out.links[0].url) == ("GitHub", "https://github.com/autre")
    assert facts_of(out)["k1"] == "GitHub — https://github.com/autre"


def test_a_link_text_without_separator_and_without_url_keeps_the_url() -> None:
    out = with_fact(data(), "k1", "Mon GitHub")
    assert (out.links[0].label, out.links[0].url) == ("Mon GitHub", "https://github.com/camille")


def test_a_bare_url_replaces_the_url_and_keeps_the_label() -> None:
    out = with_fact(data(), "k1", "https://github.com/autre")
    assert (out.links[0].label, out.links[0].url) == ("GitHub", "https://github.com/autre")


@pytest.mark.parametrize(
    "text",
    [
        "GitHub — javascript:alert(1)",
        "GitHub — github.com/autre",  # sans schéma
        "GitHub — ftp://example.org/x",
        "GitHub — https://",
        "GitHub — https://exa mple.org",
        "github.com/autre",  # une URL sans schéma et sans séparateur
        "GitHub — ",
    ],
)
def test_a_link_with_an_invalid_url_is_refused_without_echoing_it(text: str) -> None:
    with pytest.raises(AppError) as err:
        with_fact(data(), "k1", text)
    assert err.value.status_code == 422
    assert text not in str(err.value.message)


def jobs() -> MasterProfileData:
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            experiences=[Experience(role="Développeuse", company="Société Fictive")],
            education=[Education(degree="Licence", school="Université Exemple")],
        )
    )


def test_a_confirmed_experience_writes_the_role_and_the_company() -> None:
    out = with_fact(jobs(), "x1", "Lead Développeuse — Autre SA")
    assert (out.experiences[0].role, out.experiences[0].company) == (
        "Lead Développeuse",
        "Autre SA",
    )
    assert facts_of(out)["x1"] == "Lead Développeuse — Autre SA"


def test_a_confirmed_experience_with_a_suffix_keeps_one_company() -> None:
    out = with_fact(jobs(), "x1", "Développeuse — Société Fictive (CDI)")
    assert facts_of(out)["x1"] == "Développeuse — Société Fictive (CDI)"


def test_a_confirmed_experience_with_the_same_company_is_unchanged_in_shape() -> None:
    out = with_fact(jobs(), "x1", "Lead Développeuse — Société Fictive")
    assert facts_of(out)["x1"] == "Lead Développeuse — Société Fictive"


def test_a_confirmed_role_alone_keeps_the_company() -> None:
    out = with_fact(jobs(), "x1", "Lead Développeuse")
    assert facts_of(out)["x1"] == "Lead Développeuse — Société Fictive"


def test_a_confirmed_education_writes_the_degree_and_the_school() -> None:
    out = with_fact(jobs(), "f1", "Master — École B")
    assert (out.education[0].degree, out.education[0].school) == ("Master", "École B")
    assert facts_of(out)["f1"] == "Master — École B"


def test_em_dash_still_changes_company() -> None:
    out = with_fact(jobs(), "x1", "Développeuse — Autre SA")
    assert (out.experiences[0].role, out.experiences[0].company) == ("Développeuse", "Autre SA")
    assert facts_of(out)["x1"] == "Développeuse — Autre SA"
    school = with_fact(jobs(), "f1", "Master — École B")
    assert (school.education[0].degree, school.education[0].school) == ("Master", "École B")


@pytest.mark.parametrize("dash", ["–", "-"])
def test_spaced_dash_restating_current_company_splits(dash: str) -> None:
    """Un « – » ou « - » espacé coupe quand ce qui le suit est l'entreprise (ou l'école) actuelle,
    à la normalisation près : seul l'intitulé change (D137 n° 2)."""
    out = with_fact(jobs(), "x1", f"Lead Développeuse {dash} société fictive")
    assert (out.experiences[0].role, out.experiences[0].company) == (
        "Lead Développeuse",
        "Société Fictive",
    )
    school = with_fact(jobs(), "f1", f"Master {dash} Universite Exemple")
    assert (school.education[0].degree, school.education[0].school) == (
        "Master",
        "Université Exemple",
    )


@pytest.mark.parametrize("dash", ["–", "-"])
@pytest.mark.parametrize(
    ("target", "text"),
    [
        ("x1", "Développeuse {d} IA générative"),
        ("x1", "Développeuse {d} Autre SA"),
        ("f1", "Master Informatique {d} Parcours IA"),
    ],
)
def test_spaced_hyphen_title_without_company_is_422(dash: str, target: str, text: str) -> None:
    """Un intitulé à tiret espacé n'est pas « Rôle — Entreprise » : jamais une entreprise ou une
    école devinée ; 422 `ambiguous_separator`, sans écho de l'entrée."""
    given = text.format(d=dash)
    with pytest.raises(AppError) as err:
        with_fact(jobs(), target, given)
    assert (err.value.status_code, err.value.code) == (422, "ambiguous_separator")
    assert "em dash" in err.value.message and "Role — Employer" in err.value.message
    assert given not in err.value.message and err.value.details == {"fields": ["after"]}


def test_link_label_with_a_spaced_hyphen_and_no_url_stays_a_label_change() -> None:
    out = with_fact(data(), "k1", "Portfolio - Design")
    assert (out.links[0].label, out.links[0].url) == (
        "Portfolio - Design",
        "https://github.com/camille",
    )


def test_experience_without_separator_keeps_role_only_rule_documented() -> None:
    """D137 n° 2 : un texte sans séparateur ne change que le rôle, l'entreprise reste."""
    out = with_fact(jobs(), "x1", "Lead Développeuse Autre SA")
    assert (out.experiences[0].role, out.experiences[0].company) == (
        "Lead Développeuse Autre SA",
        "Société Fictive",
    )


def test_hyphenated_role_is_not_split() -> None:
    out = with_fact(jobs(), "x1", "Data-scientist — Autre SA")
    assert (out.experiences[0].role, out.experiences[0].company) == ("Data-scientist", "Autre SA")
    alone = with_fact(jobs(), "x1", "Data-scientist")  # trait d'union collé : pas un séparateur
    assert (alone.experiences[0].role, alone.experiences[0].company) == (
        "Data-scientist",
        "Société Fictive",
    )


def test_the_last_em_dash_wins_over_a_spaced_hyphen() -> None:
    out = with_fact(jobs(), "x1", "Développeuse - IA — Autre SA")
    assert (out.experiences[0].role, out.experiences[0].company) == (
        "Développeuse - IA",
        "Autre SA",
    )


def test_link_label_split_on_a_spaced_hyphen_or_en_dash() -> None:
    for dash in ("–", "-"):
        out = with_fact(data(), "k1", f"Mon-GitHub {dash} https://github.com/autre")
        assert (out.links[0].label, out.links[0].url) == ("Mon-GitHub", "https://github.com/autre")


def test_language_parenthesis_before_colon() -> None:
    out = with_fact(data(), "l1", "Anglais (TOEIC: 950)")
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais", "TOEIC: 950")


def test_language_colon_before_a_parenthesis_still_splits_on_the_colon() -> None:
    out = with_fact(data(), "l1", "Anglais : C1 (courant)")
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais", "C1 (courant)")


@pytest.mark.parametrize("bad", ["<", ">", '"'])
@pytest.mark.parametrize("where", ["path", "query"])
def test_url_with_angle_brackets_or_quote_is_invalid(bad: str, where: str) -> None:
    url = f"https://example.org/a{bad}b" if where == "path" else f"https://example.org/?q={bad}"
    with pytest.raises(AppError) as err:
        with_fact(data(), "k1", f"GitHub — {url}")
    assert err.value.status_code == 422
    assert bad not in str(err.value.message)
