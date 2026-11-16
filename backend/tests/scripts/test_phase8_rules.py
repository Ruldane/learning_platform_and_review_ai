"""Règles pures du contrôle de la phase 8 : salaire relu dans la page, nombres des rubriques, heure
réglée du brief, textes cherchés dans les journaux. Aucun réseau."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase8_rules import (
    check_report,
    check_rubrics,
    check_same_day,
    log_extras,
    rubric_numbers,
    salary_missing,
    target_moment,
)
from tests.scripts.phase8_support import brief_json, radar_run

PARIS = ZoneInfo("Europe/Paris")


@pytest.mark.parametrize(
    ("salary", "page", "missing"),
    [
        ("45-55 k€", "de 45 à 55 k€ par an", False),
        ("45-55 k€", "de 450 à 55 k€", True),  # 45 n'est pas 450
        ("45-55 k€", "de 45 à 5 k€", True),
        ("selon profil", "selon profil", True),  # un salaire sans chiffre n'est jamais gardé
        ("45 000 €", "45 000 euros", False),
    ],
)
def test_a_reported_salary_needs_each_of_its_figures_in_the_page(
    salary: str, page: str, missing: bool
) -> None:
    assert salary_missing(salary, page) is missing


def test_the_rubric_numbers_are_their_integers_and_the_sizes_of_their_lists() -> None:
    numbers = rubric_numbers(brief_json())

    assert {"45", "12", "2", "1", "600", "120", "3", "9", "4"} <= numbers
    assert "99" not in numbers


def test_the_planned_time_is_three_minutes_later_to_the_minute() -> None:
    now = datetime(2026, 11, 16, 10, 0, 12, tzinfo=PARIS)

    assert target_moment(now).strftime("%H:%M:%S") == "10:03:00"
    check_same_day("planification", now, target_moment(now))
    late = datetime(2026, 11, 16, 23, 58, tzinfo=PARIS)
    with pytest.raises(CheckFailed, match="minuit"):
        check_same_day("planification", late, target_moment(late))


def test_log_extras_keep_this_runs_texts_once_and_skip_the_short_ones() -> None:
    run = radar_run(zone="Pau")  # 3 signes : trop banal pour être cherché dans les journaux

    extras = log_extras(run, brief_json())

    assert "Développeur Python" in extras and "Pau" not in extras
    assert extras.count("https://jobs.example/offre-a") == 1
    assert "Garde ton rythme de 4 jours." in extras and "Un guide" in extras
    assert log_extras(None, None) == []


def test_a_report_without_the_seven_rubrics_names_the_missing_ones() -> None:
    brief = brief_json()
    del brief["week"], brief["advice"]

    with pytest.raises(CheckFailed, match="week, advice"):
        check_rubrics("rubriques", brief)


def test_a_report_with_unsorted_scores_is_refused() -> None:
    run = radar_run()
    run["offers"] = list(reversed(run["offers"]))

    with pytest.raises(CheckFailed, match="du meilleur au moindre"):
        check_report("rapport", run)
