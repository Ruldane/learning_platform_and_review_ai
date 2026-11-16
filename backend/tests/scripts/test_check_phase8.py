"""Contrôle de la phase 8, parties `planifie` et `radar`, contre une fausse API
(`phase8_support`) : le chemin heureux, chaque message d'échec, la remise des réglages après un
échec. Aucun réseau ni LLM, rien d'affiché qui soit une donnée (poste, lien, entreprise)."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from scripts.check_phase8 import PLANIFIE_STEPS, RADAR_STEPS
from tests.scripts.phase8_support import NOON, FakeApi, fails, play, radar_run


@pytest.fixture(autouse=True)
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.phase8_common.POLL_S", 0.0)
    monkeypatch.setattr("scripts.phase8_plan.local_now", lambda zone: NOON)


# -- planifie ---------------------------------------------------------------------------------


async def test_planned_brief_is_created_by_the_schedule_and_the_time_is_restored(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeApi()

    done = await play(fake, "planifie")

    assert done == list(PLANIFIE_STEPS)
    assert [put["brief_time"] for put in fake.puts] == ["10:03", "07:00"]
    assert fake.puts[-1] == fake.settings and fake.settings["brief_time"] == "07:00"
    assert fake.brief is not None and fake.brief["origin"] == "schedule"
    assert (
        "GET /brief/today" not in fake.seen[: fake.seen.index("PUT /settings")]
    )  # ne crée rien avant
    assert "brief b1 créé par la tâche planifiée" in capsys.readouterr().out


async def test_planned_part_refuses_when_todays_brief_exists_and_changes_nothing() -> None:
    fake = FakeApi()
    fake.create_brief("opening")

    await fails(fake, "planifie", "préalable", "existe déjà (brief:b1:ready)")

    assert fake.puts == []


async def test_planned_part_restores_the_time_when_the_brief_never_comes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.phase8_plan.PLANNED_GRACE_S", -181.0)
    fake = FakeApi(polls=99)

    await fails(fake, "planifie", "planification", "Délai dépassé")

    assert fake.settings["brief_time"] == "07:00" and fake.puts[0]["brief_time"] == "10:03"


async def test_planned_part_fails_when_the_origin_is_not_the_schedule() -> None:
    fake = FakeApi()
    fake.brief_over = {"origin": "opening"}

    await fails(fake, "planifie", "origine", "« schedule » attendue")

    assert fake.settings["brief_time"] == "07:00"  # remise avant l'étape suivante


async def test_planned_part_refuses_the_last_minutes_before_midnight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    late = datetime(2026, 11, 16, 23, 58, tzinfo=ZoneInfo("Europe/Paris"))
    monkeypatch.setattr("scripts.phase8_plan.local_now", lambda zone: late)
    fake = FakeApi()

    await fails(fake, "planifie", "planification", "Trop près de minuit")

    assert fake.settings["brief_time"] == "07:00" and fake.brief is None


# -- radar ------------------------------------------------------------------------------------


async def test_radar_part_runs_a_fictive_run_and_restores_the_settings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeApi()

    done = await play(fake, "radar")

    assert done == list(RADAR_STEPS)
    assert fake.settings["radar_role"] == "" and fake.settings["radar_zone"] == "France"
    assert fake.puts and fake.puts[-1]["radar_zone"] == "France"
    out = capsys.readouterr().out
    assert "relevé r1 fini en" in out and "3 appel(s) LLM" in out and "0.0123 $" in out
    assert "40 page(s) lue(s) dont 4 sans offre, 8 bloquée(s), 3 offre(s) analysée(s)" in out
    assert "2 à 70 ou plus" in out and "1 vérifié(s) dans la page" in out
    for secret in ("Développeur", "Lyon", "Maison A", "Titre A", "jobs.example", "45-55"):
        assert secret not in out  # rien de reçu n'est affiché


async def test_radar_part_counts_an_unreachable_page_without_judging_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeApi()
    del fake.pages["/offre-a"]

    await play(fake, "radar")

    assert "0 vérifié(s) dans la page, 1 page(s) injoignable(s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("second", "message"),
    [
        ({"second_status": 202}, "HTTP 202"),
        ({"second_run_id": "autre"}, "autre relevé"),
    ],
    ids=["second lancement accepté", "409 d'un autre relevé"],
)
async def test_radar_part_fails_when_the_second_launch_is_not_refused_for_the_same_run(
    second: dict[str, Any], message: str
) -> None:
    fake = FakeApi()
    for name, value in second.items():
        setattr(fake, name, value)

    await fails(fake, "radar", "lancement", message)

    assert fake.settings["radar_role"] == ""  # remis même en échec


async def test_radar_part_names_the_error_code_of_a_failed_run() -> None:
    fake = FakeApi()
    fake.run = radar_run(status="failed", error_code="search_unavailable")

    await fails(fake, "radar", "relevé", "en échec (search_unavailable)")


async def test_radar_part_fails_when_the_run_is_too_slow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.phase8_radar.RADAR_S", -1.0)
    fake = FakeApi(polls=99)

    await fails(fake, "radar", "relevé", "relevé jamais fini")


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"read_count": 55, "blocked_count": 8}, "60 lectures au plus"),
        ({"analyzed": 5}, "3 offre(s) rendue(s) pour 5 analysée(s)"),
        ({"ranking": []}, "Classement vide"),
        ({"low_sample": True}, "`low_sample` incohérent"),
        ({"blocked_domains": []}, "sites bloqués"),
        ({"not_postings": 39}, "39 sans offre > 40 lue(s)"),
    ],
    ids=["plafond", "offres", "classement", "échantillon", "sites bloqués", "pages sans offre"],
)
async def test_radar_part_fails_on_an_inconsistent_report(
    over: dict[str, Any], message: str
) -> None:
    fake = FakeApi()
    fake.run = radar_run(**over)

    await fails(fake, "radar", "rapport", message)


async def test_radar_part_fails_when_a_reported_salary_is_not_in_the_page() -> None:
    fake = FakeApi()
    fake.pages["/offre-a"] = "Salaire 45 à 5 k€ par an"  # 55 absent

    await fails(fake, "radar", "rapport", "Salaire de l'offre n° 1 absent de sa page relue")
