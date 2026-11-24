"""Règles du contrôle de la phase 7 (`phase7_rules`) : fonctions pures, chaque règle tenue puis
violée. Les messages d'échec ne recopient jamais un texte, un terme ni une entreprise."""

import io
import zipfile
from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase7_rules import (
    KIT_ORDER,
    SALARY_BLANK,
    check_dossier,
    check_form,
    check_items,
    check_lengths,
    check_letter,
    check_logs,
    check_to_check,
    check_zip,
    profile_text,
    speaks,
    term_in_profile,
)

FRENCH = "Je construis des solutions fiables avec soin et je partage ce que j'apprends. "
ENGLISH = "I build reliable solutions with care and I share what I learn every day. "
PROFILE = {
    "identity": {"name": "Camille Exemple", "email": "camille@example.org", "phone": "+33 6 12"},
    "experiences": [
        {
            "id": "x1",
            "role": "Développeuse IA",
            "achievements": [{"text": "Réduit de 30 % le coût"}],
        }
    ],
    "skills": [{"name": "Python"}, {"name": "Docker"}],
    "links": [{"url": "https://example.org/camille"}],
}


def item(kind: str, content: str = "texte", status: str = "ready", **over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": f"id-{kind}",
        "kind": kind,
        "status": status,
        "content": content,
        "flags": [],
        "salary_fields": 0,
        "words": None,
        "error": None,
        "sources": [],
        "edited": False,
    }
    return base | over


def words(text: str, count: int) -> str:
    return " ".join((text.split() * count)[:count])


def test_logs_pass_and_name_the_leaked_pattern_without_the_data() -> None:
    assert check_logs("journaux", "ligne 1\nligne 2\n") == 2

    for leaked in ("Atelier Relance 3", "Alex Contrôle", "controle-phase-7", "Camille"):
        with pytest.raises(CheckFailed) as failed:
            check_logs("journaux", f"avant {leaked} après")
        assert failed.value.step == "journaux"
        assert leaked not in str(failed.value)
    with pytest.raises(CheckFailed):
        check_logs("journaux", "Fabrique Cèdre", ("Fabrique Cèdre",))


def test_profile_text_keeps_facts_but_not_contact_or_links() -> None:
    text = profile_text(PROFILE)

    assert "Réduit de 30 % le coût" in text and "Python" in text and "Camille Exemple" in text
    assert "+33" not in text and "camille@example.org" not in text
    assert "example.org/camille" not in text
    assert "x1" not in text.split()


@pytest.mark.parametrize(
    ("term", "present"),
    [
        ("Python", True),
        ("python", True),
        ("Dockers", True),  # pluriel
        ("30%", True),
        ("Kubernetes", False),
        ("6", False),  # le téléphone n'est pas un fait
        ("", False),
    ],
)
def test_term_in_profile(term: str, present: bool) -> None:
    assert term_in_profile(term, profile_text(PROFILE)) is present


def test_speaks_the_posting_language() -> None:
    assert speaks(FRENCH * 3, "fr") and not speaks(FRENCH * 3, "en")
    assert speaks(ENGLISH * 3, "en") and not speaks(ENGLISH * 3, "fr")
    assert not speaks("", "fr")


def test_letter_needs_250_to_350_words_in_the_posting_language() -> None:
    assert check_letter("kit", item("letter", words(FRENCH, 300)), "fr") == 300
    for count in (249, 351):
        with pytest.raises(CheckFailed, match=f"{count} mot"):
            check_letter("kit", item("letter", words(FRENCH, count)), "fr")
    with pytest.raises(CheckFailed, match="langue de l'offre"):
        check_letter("kit", item("letter", words(ENGLISH, 300)), "fr")
    check_letter("kit", item("letter", words(ENGLISH, 300)), "en")


def test_lengths_of_the_other_written_pieces() -> None:
    pitch = item("pitch", words(FRENCH, 150))
    invitation, message = "Bonjour, votre poste m'intéresse.", words(FRENCH, 100)
    linkedin = item("linkedin", f"{invitation}\n\n---\n\n{message}")
    followups = item("followups", f"{words(FRENCH, 80)}\n\n---\n\n{words(FRENCH, 80)}")
    for good in (pitch, linkedin, followups, item("cv", "")):
        check_lengths("kit", good)

    too_long = [
        item("pitch", words(FRENCH, 200)),
        item("linkedin", f"{'x' * 301}\n\n---\n\n{message}"),
        item("linkedin", f"{invitation}\n\n---\n\n{words(FRENCH, 151)}"),
        item("linkedin", message),  # pas de séparateur
        item("followups", f"{words(FRENCH, 121)}\n\n---\n\n{words(FRENCH, 80)}"),
        item("followups", words(FRENCH, 80)),
    ]
    for bad in too_long:
        with pytest.raises(CheckFailed):
            check_lengths("kit", bad)
    check_lengths("kit", item("pitch", words(FRENCH, 200), status="to_check"))  # nouvel essai raté


def test_form_never_fills_a_salary_answer() -> None:
    blank = f"### Quelles sont vos prétentions salariales ?\n{SALARY_BLANK}\n\n### Permis B ?\nOui."
    assert check_form("kit", item("form_answers", blank, salary_fields=1)) == 1
    assert check_form("kit", item("form_answers", "Aucune question éliminatoire repérée.")) == 0

    filled = "### Quel salaire espérez-vous ?\n45 k€ brut."
    with pytest.raises(CheckFailed, match="salariale"):
        check_form("kit", item("form_answers", filled))
    with pytest.raises(CheckFailed, match="salary_fields"):
        check_form("kit", item("form_answers", blank, salary_fields=0))


def test_to_check_pieces_name_terms_that_are_really_absent_from_the_profile() -> None:
    profile = profile_text(PROFILE)
    flagged = item("pitch", words(FRENCH, 150), status="to_check", flags=["Kubernetes", "12"])
    assert check_to_check("kit", flagged, profile) == 2

    in_profile = item("pitch", "t", status="to_check", flags=["Kubernetes", "Python"])
    with pytest.raises(CheckFailed) as present:
        check_to_check("kit", in_profile, profile)
    assert "n° 1" in str(present.value) and "Python" not in str(present.value)

    with pytest.raises(CheckFailed, match="sans terme nommé"):
        check_to_check("kit", item("pitch", words(FRENCH, 150), status="to_check"), profile)
    # Mots hors bornes : c'est la raison, aucun terme n'est requis.
    assert check_to_check("kit", item("pitch", words(FRENCH, 40), status="to_check"), profile) == 0
    assert check_to_check("kit", item("letter", words(FRENCH, 40), status="to_check"), profile) == 0

    blank = item("form_answers", f"### Salaire ?\n{SALARY_BLANK}", status="to_check")
    assert check_to_check("kit", blank, profile) == 0
    with pytest.raises(CheckFailed, match="sans terme ni réponse vide"):
        check_to_check("kit", item("form_answers", "### Q ?\nOui.", status="to_check"), profile)
    assert check_to_check("kit", item("company_brief", "x", status="to_check"), profile) == 0


def test_dossier_needs_sources_and_citations_that_point_at_them() -> None:
    sources = [
        {"rank": 1, "url": "https://a.example.org", "title": None},
        {"rank": 2, "url": "https://b.example.org", "title": "B"},
    ]
    good = item("company_brief", "Éditeur [1]. Produit [1, 2].", sources=sources)
    assert check_dossier("kit", good) == 2

    bad = [
        item("company_brief", "Texte [1]."),  # aucune source
        item("company_brief", "Texte [3].", sources=sources),  # citation sans source
        item("company_brief", "Texte.", sources=sources),  # aucune citation
        item("company_brief", "Texte [1].", sources=[{**sources[1], "rank": 2}]),  # rangs
        item("company_brief", "Texte [1].", sources=[{**sources[0], "url": "ftp://x"}]),  # lien
    ]
    for piece in bad:
        with pytest.raises(CheckFailed):
            check_dossier("kit", piece)


def test_items_are_seven_in_the_fixed_order_and_none_missing() -> None:
    items = [item(kind) for kind in KIT_ORDER]
    check_items("kit", items)

    with pytest.raises(CheckFailed, match="7"):
        check_items("kit", items[:6])
    with pytest.raises(CheckFailed, match="7"):
        check_items("kit", list(reversed(items)))
    for status in ("pending", "failed"):
        broken = [*items[:6], item("pitch", status=status)]
        with pytest.raises(CheckFailed, match=f"pitch \\({status}\\)"):
            check_items("kit", broken)
    with pytest.raises(CheckFailed, match="vide"):
        check_items("kit", [*items[:6], item("pitch", "  ")])


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_zip_is_readable_with_one_file_per_piece_the_pdf_and_the_readme() -> None:
    items = [item(kind, f"contenu {kind}") for kind in KIT_ORDER]
    items[3]["status"] = "to_check"
    files = {
        f"{rank:02d}_{kind}.md": f"contenu {kind}\n".encode()
        for rank, kind in enumerate(KIT_ORDER, 1)
    }
    files |= {"CV_Camille.pdf": b"%PDF-1.4", "README.txt": b"- 04_followups.md (Follow-ups)"}

    assert check_zip("kit", _zip(files), items) == 9

    def without(name: str) -> bytes:
        return _zip({k: v for k, v in files.items() if k != name})

    broken = [
        b"pas un zip",
        without("03_linkedin.md"),
        _zip({**files, "02_letter.md": b"autre"}),
        without("CV_Camille.pdf"),
        _zip({**files, "CV_Camille.pdf": b"texte"}),
        without("README.txt"),
        _zip({**files, "README.txt": b"- None"}),
    ]
    for body in broken:
        with pytest.raises(CheckFailed):
            check_zip("kit", body, items)
