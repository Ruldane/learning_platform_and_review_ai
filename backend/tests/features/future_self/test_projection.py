"""Le rythme observé, les scénarios et les recommandations partagent les mêmes écarts."""

from datetime import date

from app.features.future_self.projection import ChapterWork, ProjectionInput, project
from app.features.gap.service.score import GapRow

TODAY = date(2026, 11, 16)


def _offers() -> tuple[tuple[GapRow, ...], ...]:
    python = GapRow("Python", True, "validated", "in_program", None)
    rag = GapRow("Ràg", True, None, "in_program", 1)
    agents = GapRow("Agents", True, "in_progress", "in_program", 2)
    language = GapRow("Permis", True, None, "out_of_scope", None)
    unrelated = GapRow("Finance", True, None, "to_add", None)
    return ((python,), (rag,), (rag, agents), (agents, language), (unrelated,))


def _chapters() -> tuple[ChapterWork, ...]:
    return (
        ChapterWork("p", "rag", "lesson-rag", "Recherche", 120, ("RAG",)),
        ChapterWork("p", "agents", None, "Agents", 120, ("Agents",)),
        ChapterWork("p", "unavailable", None, "Sans charge prévue", 0, ("Finance", "Permis")),
    )


def test_observed_and_other_weekly_availability_use_same_remaining_chapters() -> None:
    result = project(
        ProjectionInput(
            today=TODAY,
            history_started_on=date(2026, 10, 19),
            studied=(
                (date(2026, 10, 16), 600),  # en dehors des quatre semaines
                (date(2026, 10, 22), 240),
                (date(2026, 11, 5), 240),
                (TODAY, 600),  # semaine en cours ignorée
            ),
            planned_weekly_minutes=180,
            alternative_weekly_minutes=240,
            target_percent=60,
            offers=_offers(),
            chapters=_chapters(),
        )
    )
    assert (result.offer_count, result.current_percent, result.observed_weeks) == (5, 20, 4)
    assert [
        (s.kind, s.weekly_minutes, s.target_date, s.projected_percent) for s in result.scenarios
    ] == [
        ("observed", 120, date(2026, 11, 30), 60),
        ("planned", 180, date(2026, 11, 26), 60),
        ("alternative", 240, date(2026, 11, 23), 60),
    ]
    first, second = result.recommendations
    assert first.chapter.lesson_id == "lesson-rag"
    assert (first.offers_unlocked, first.offers_improved) == (1, 2)
    assert (second.chapter.module_id, second.offers_unlocked, second.offers_improved) == (
        "agents",
        0,
        2,
    )


def test_insufficient_history_and_offers_do_not_create_false_predictions() -> None:
    result = project(
        ProjectionInput(today=TODAY, planned_weekly_minutes=180, alternative_weekly_minutes=240)
    )
    assert result.offer_count == 0 and result.current_percent is None
    assert result.uncertainty == ("insufficient_study_history", "no_offer_sample")
    assert all(s.target_date is None and s.projected_percent is None for s in result.scenarios)
    assert not result.recommendations


def test_zero_observed_pace_does_not_forecast_a_date_with_work_remaining() -> None:
    result = project(
        ProjectionInput(
            today=TODAY,
            history_started_on=date(2026, 10, 25),  # trois semaines complètes
            planned_weekly_minutes=180,
            target_percent=60,
            offers=_offers(),
            chapters=_chapters(),
        )
    )
    assert result.observed_weeks == 3
    observed, planned = result.scenarios
    assert (observed.weekly_minutes, observed.target_date, observed.projected_percent) == (
        0,
        None,
        20,
    )
    assert planned.target_date == date(2026, 11, 26)
    assert "small_offer_sample" in result.uncertainty


def test_target_already_met_and_rows_from_cv_reviews_do_not_change_coverage() -> None:
    ready = GapRow("Python", True, "proven", "in_program", 1)
    cv_review = GapRow("Autre", True, None, "to_add", None, "cv_review")
    result = project(ProjectionInput(today=TODAY, offers=((ready, cv_review), (cv_review,), ())))
    assert result.offer_count == 1 and result.current_percent == 100
    assert all(s.target_date == TODAY and s.projected_percent == 100 for s in result.scenarios)


def test_non_learnable_requirement_cannot_be_unlocked_by_homonymous_chapter() -> None:
    permit = GapRow("Permis", True, None, "out_of_scope", None)
    result = project(
        ProjectionInput(
            today=TODAY,
            planned_weekly_minutes=180,
            offers=((permit,),),
            chapters=(ChapterWork("p", "lesson", None, "Permis", 120, ("Permis",)),),
        )
    )
    assert result.current_percent == 0
    assert result.scenarios[-1].target_date is None and result.scenarios[-1].projected_percent == 0
    assert not result.recommendations


def test_readiness_reuses_the_radar_high_match_threshold_and_checks_required_skills() -> None:
    needed = GapRow("Python", True, "validated", "in_program", None)
    declared = GapRow("Rust", True, "declared", "in_program", None)
    acquired = GapRow("Docker", False, "proven", "in_program", None)
    missing = GapRow("Kubernetes", False, None, "to_add", None)
    other = GapRow("SQL", False, "validated", "in_program", None)
    result = project(
        ProjectionInput(
            today=TODAY, offers=((needed, acquired, missing), (declared, acquired, other))
        )
    )
    assert (
        result.current_percent == 50
    )  # 75 % avec l'obligatoire acquis, 80 % avec l'obligatoire déclaré
