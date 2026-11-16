"""Contrôle de la phase 8, parties `projets` et `tout`, contre une fausse API
(`phase8_projects_support`) : énoncé prêt, attendu ou relancé, rendu multipart, évaluation, issues
validé (avec ou sans brouillons) et à reprendre, journaux. Aucun réseau ni LLM, rien d'affiché qui
soit un titre, un critère, un lien ou une phrase du README."""

from typing import Any

import pytest

from scripts.check_phase8 import PROJETS_STEPS, TOUT_STEPS
from scripts.phase8_projects_rules import REPO_URL
from tests.scripts.phase8_projects_support import (
    BRIEF,
    ENTRY,
    README_LINE,
    TITLE,
    ProjectsApi,
    project_json,
)
from tests.scripts.phase8_support import NOON, fails, play


@pytest.fixture(autouse=True)
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.phase8_common.POLL_S", 0.0)
    monkeypatch.setattr("scripts.phase4_steps.POLL_S", 0.0)
    monkeypatch.setattr("scripts.phase8_plan.local_now", lambda zone: NOON)


# -- issue validée ----------------------------------------------------------------------------


async def test_projects_part_validates_a_project_and_adds_it_to_the_profile_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = ProjectsApi()

    done = await play(fake, "projets")

    assert done == list(PROJETS_STEPS)
    out = capsys.readouterr().out
    assert "projet p1 (semaine 1, statut todo) : 3 critères, 4 h, 2 compétence(s)" in out
    assert "description" in out and "1 phrase(s) du README relevée(s)" in out
    assert "verdict validated, 3 critère(s) atteint(s) sur 3, dépôt read" in out
    assert "3 appel(s) LLM ; 0.0042 $" in out
    assert "4 brouillons : 3 prêt(s), 1 à vérifier" in out and "2 compétence(s) à prouve" in out
    assert "profil 3 -> 4, projet entré une fois ; second ajout refusé" in out
    assert fake.entries == 1 and fake.profile_version == 4
    for secret in (TITLE, BRIEF["criteria"][0], REPO_URL, README_LINE, ENTRY["name"]):
        assert secret not in out


async def test_the_submission_is_a_multipart_form_with_a_description_and_a_link_only() -> None:
    fake = ProjectsApi()

    await play(fake, "projets")

    assert fake.submit_type.startswith("multipart/form-data")
    form = fake.submit_form.decode()
    assert 'name="description"' in form and REPO_URL in form and "screenshots" not in form


async def test_projects_part_reports_drafts_unavailable_as_a_legitimate_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = ProjectsApi(outcome="no_drafts")

    await play(fake, "projets")

    out = capsys.readouterr().out
    assert "brouillons indisponibles (issue légitime" in out and fake.entries == 1
    assert fake.profile_projects[-1]["name"] == f"{TITLE} p1"  # l'entrée fictive de l'énoncé


# -- issue à reprendre ------------------------------------------------------------------------


async def test_projects_part_counts_the_unmet_criteria_and_leaves_the_profile_alone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = ProjectsApi(outcome="to_redo")

    done = await play(fake, "projets")

    assert done == list(PROJETS_STEPS)
    out = capsys.readouterr().out
    assert "verdict to_redo, 1 critère(s) atteint(s) sur 3" in out
    assert (
        "2 critère(s) non atteint(s), nommés ; aucun brouillon ; profil inchangé (version 3)" in out
    )
    assert fake.entries == 0 and fake.profile_version == 3
    assert not any("skills/graph" in call for call in fake.seen)


# -- énoncé attendu, relancé, aucun projet ----------------------------------------------------


async def test_a_pending_brief_is_waited_for(capsys: pytest.CaptureFixture[str]) -> None:
    fake = ProjectsApi([project_json("p1", "brief_pending")], polls=2)

    await play(fake, "projets")

    assert "statut brief_pending, attendu" in capsys.readouterr().out
    assert fake.brief_posts == []


async def test_a_failed_brief_gets_one_new_try(capsys: pytest.CaptureFixture[str]) -> None:
    fake = ProjectsApi([project_json("p1", "brief_failed")], polls=1)

    await play(fake, "projets")

    assert fake.brief_posts == ["p1"]
    assert "un nouvel essai lancé (le seul)" in capsys.readouterr().out


async def test_a_brief_that_fails_again_stops_the_check() -> None:
    fake = ProjectsApi([project_json("p1", "brief_failed")])
    fake.polls = 99

    original = fake._brief_tick

    def fail_at_once(project: dict[str, Any]) -> None:
        original(project)
        project["status"] = "brief_failed"

    fake._brief_tick = fail_at_once  # type: ignore[method-assign]
    await fails(fake, "projets", "énoncé", "en échec (brief_failed)")


async def test_a_validated_project_is_skipped_for_the_next_todo_one() -> None:
    done = project_json("p1", "validated", week=1)
    fake = ProjectsApi([done, project_json("p2", "todo", week=2)])

    await play(fake, "projets")

    assert fake.projects["p2"]["status"] == "validated" and fake.projects["p1"]["submissions"] == []


async def test_no_eligible_project_is_said_clearly() -> None:
    fake = ProjectsApi([project_json("p1", "validated"), project_json("p2", "reviewing")])

    await fails(
        fake, "projets", "énoncé", "Aucun projet éligible (2 projet(s) : reviewing 1, validated 1)"
    )
    await fails(ProjectsApi([]), "projets", "énoncé", "Aucun projet éligible (0 projet(s) : aucun)")


# -- échecs -----------------------------------------------------------------------------------


async def test_a_brief_out_of_bounds_stops_before_any_submission() -> None:
    fake = ProjectsApi()
    fake.projects["p1"]["brief"]["hours"] = 9

    await fails(fake, "projets", "énoncé", "9 h annoncées")
    assert fake.submit_form == b""


async def test_a_missing_validated_profile_stops_before_any_submission() -> None:
    fake = ProjectsApi()
    fake._profile = lambda: {"validated": None, "draft": None}  # type: ignore[method-assign]

    await fails(fake, "projets", "rendu", "Aucun profil maître validé")
    assert fake.submit_form == b""


async def test_an_unreadable_repo_is_a_failed_evaluation_step() -> None:
    await fails(ProjectsApi(repo_status="unreadable"), "projets", "évaluation", "unreadable")


async def test_a_skill_not_at_prouve_fails_before_the_profile_is_touched() -> None:
    fake = ProjectsApi()
    fake.level = "valide"

    await fails(fake, "projets", "suites", "2 compétence(s) sur 2 pas à « prouve »")
    assert fake.entries == 0


async def test_a_profile_that_moved_before_the_entry_fails() -> None:
    fake = ProjectsApi()
    original = fake._finish

    def finish_and_move() -> None:
        original()
        fake.profile_version += 1

    fake._finish = finish_and_move  # type: ignore[method-assign]
    await fails(fake, "projets", "suites", "a bougé avant `profile-entry`")
    assert fake.entries == 0


# -- journaux ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("leak", "secret"),
    [
        (f"projet {TITLE} p1 rendu", "Mini API"),
        (f"lien {REPO_URL} lu", "psf/requests"),
        (f"phrase {README_LINE}", "bibliothèque HTTP"),
        (f"critère {BRIEF['criteria'][1]}", "tests passent"),
        ("brouillon Brouillon cv_line.", "Brouillon cv"),
        ("retour Commentaire du critère 2.", "Commentaire"),
    ],
)
async def test_logs_step_fails_on_project_data_without_copying_it(leak: str, secret: str) -> None:
    await fails(
        ProjectsApi(), "projets", "journaux", "Donnée personnelle", logs=f"INFO ok\n{leak}\n"
    )


async def test_logs_step_accepts_clean_logs(capsys: pytest.CaptureFixture[str]) -> None:
    await play(ProjectsApi(), "projets", logs="INFO projet p1 évalué\nINFO session s-proj finie\n")

    assert "2 ligne(s) relue(s), sans donnée" in capsys.readouterr().out


# -- tout -------------------------------------------------------------------------------------


async def test_everything_runs_radar_brief_then_projects_with_one_logs_step(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = ProjectsApi()

    done = await play(fake, "tout")

    assert done == list(TOUT_STEPS)
    assert done.index("lancement") < done.index("rubriques") < done.index("énoncé")
    assert done.count("journaux") == 1 and done[-1] == "journaux"
    assert "sans donnée" in capsys.readouterr().out


async def test_everything_catches_a_radar_text_and_a_project_text_in_the_logs() -> None:
    await fails(ProjectsApi(), "tout", "journaux", "Donnée personnelle", logs="zone Lyon\n")
    await fails(ProjectsApi(), "tout", "journaux", "Donnée personnelle", logs=f"{REPO_URL}\n")
