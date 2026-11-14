"""Un fait confirmé en revue entre au profil maître (I-2, re-revue de la vague de corrections) :
une langue s'écrit « Nom — niveau », un lien « Libellé — URL » ; ni l'un ni l'autre ne finit
dans le nom ou le libellé. Une URL invalide est refusée par le 422 habituel."""

import pytest

from app.agents.tools.cv_schema import (
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


def test_a_language_text_without_separator_keeps_the_level() -> None:
    out = with_fact(data(), "l1", "Anglais courant")
    assert (out.languages[0].name, out.languages[0].level) == ("Anglais courant", "B2")


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
