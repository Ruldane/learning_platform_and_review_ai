"""Règles pures du radar : classement, évolution, alertes, score, salaire (8.1, P5 à P9)."""

from typing import Any

from app.db.models.skills import SkillLevel
from app.features.radar.service.rules import (
    ALERT_MAX,
    ALERT_MIN_POSTINGS,
    ALERT_SHARE,
    ENRICH_MAX,
    ENRICH_SHARE,
    HIGH_MATCH,
    MAX_CANDIDATES,
    MAX_READS,
    MAX_RUN,
    MIN_RUN,
    SkillFreq,
    alert_message,
    enrich_names,
    evolution,
    low_sample,
    posting_score,
    program_alerts,
    rank_skills,
    salary_shown,
)


def skills(names: list[str], required: bool = True) -> list[dict[str, Any]]:
    return [{"name": name, "required": required} for name in names]


def ok(names: list[str], **extra: Any) -> dict[str, Any]:
    return {"read": "ok", "skills": skills(names), **extra}


def blocked(names: list[str]) -> dict[str, Any]:
    return {"read": "blocked", "skills": skills(names)}


def freq(name: str, share: float, rank: int = 1, count: int = 1) -> SkillFreq:
    return SkillFreq(skill=name, norm=name.casefold(), count=count, share=share, rank=rank)


def test_constants() -> None:
    assert (MIN_RUN, MAX_RUN, MAX_READS, MAX_CANDIDATES, HIGH_MATCH) == (30, 50, 60, 80, 70)
    assert (ALERT_SHARE, ALERT_MIN_POSTINGS, ALERT_MAX) == (0.5, 10, 5)
    assert (ENRICH_SHARE, ENRICH_MAX) == (0.3, 15)


def test_rank_skills_counts_once_per_posting() -> None:
    r = rank_skills([ok(["Python", "python", "SQL"]), ok(["Python"]), blocked(["Go"])])
    assert [(s.skill, s.count, s.share) for s in r] == [("Python", 2, 1.0), ("SQL", 1, 0.5)]
    assert [s.norm for s in r] == ["python", "sql"]


def test_rank_skills_displays_the_most_frequent_form() -> None:
    r = rank_skills([ok(["python"]), ok(["Python"]), ok(["Python"]), ok(["PYTHON"])])
    assert [(s.skill, s.count) for s in r] == [("Python", 4)]


def test_rank_skills_ties_share_a_rank() -> None:
    postings = [ok(["A", "B", "C"]), ok(["A", "B"]), ok(["A"])] + [ok(["D"])]
    r = rank_skills(postings)
    assert [(s.skill, s.count, s.rank) for s in r] == [
        ("A", 3, 1),
        ("B", 2, 2),
        ("C", 1, 3),
        ("D", 1, 3),
    ]
    tied = rank_skills([ok(["A", "B"]), ok(["A", "B"]), ok(["C"]), ok(["D"])])
    assert [s.rank for s in tied] == [1, 1, 3, 3]
    gap = rank_skills([ok(["A", "B", "C"]), ok(["A", "B", "C"]), ok(["A", "D"])])
    assert [(s.skill, s.rank) for s in gap] == [("A", 1), ("B", 2), ("C", 2), ("D", 4)]


def test_rank_skills_orders_ties_by_normalized_name() -> None:
    r = rank_skills([ok(["Zig", "docker", "Ansible"])])
    assert [s.skill for s in r] == ["Ansible", "docker", "Zig"]


def test_rank_skills_share_is_rounded_half_up_to_hundredths() -> None:
    postings = [ok(["Rust"])] + [ok(["Go"]) for _ in range(7)]
    assert rank_skills(postings)[1].share == 0.13  # 1/8 = 12,5 % -> 13
    third = rank_skills([ok(["Rust"]), ok(["Go"]), ok(["Go"])])
    assert third[0].share == 0.67 and third[1].share == 0.33


def test_rank_skills_only_counts_readable_analysed_postings() -> None:
    postings = [
        ok(["Python"]),
        {"read": "not_posting", "skills": skills(["Python"])},
        {"read": "extract_failed"},
        {"read": "ok", "skills": None},  # lue mais pas analysée
        {"read": "ok"},
        ok([]),  # analysée, sans compétence : compte au dénominateur
    ]
    r = rank_skills(postings)
    assert [(s.skill, s.count, s.share) for s in r] == [("Python", 1, 0.5)]


def test_rank_skills_ignores_blank_names_and_empty_input() -> None:
    assert rank_skills([]) == []
    assert rank_skills([ok(["", "  "])]) == []


def test_evolution_points_rank_and_new() -> None:
    previous = [
        freq("Python", 0.62, rank=1),
        freq("SQL", 0.5, rank=2),
        freq("Spark", 0.45, rank=3),
        freq("Kafka", 0.42, rank=4),
        freq("dbt", 0.40, rank=5),
    ]
    current = [
        freq("Python", 0.7, rank=1),
        freq("dbt", 0.62, rank=2),
        freq("SQL", 0.5, rank=3),
        freq("Rust", 0.3, rank=4),
    ]
    out = {t.skill: t for t in evolution(current, previous)}
    assert (out["dbt"].delta_share, out["dbt"].delta_rank, out["dbt"].new) == (22, 3, False)
    assert (out["SQL"].delta_share, out["SQL"].delta_rank) == (0, -1)
    assert (out["Python"].delta_share, out["Python"].delta_rank) == (8, 0)
    assert (out["Rust"].delta_share, out["Rust"].delta_rank, out["Rust"].new) == (None, None, True)
    assert [t.skill for t in evolution(current, previous)] == ["Python", "dbt", "SQL", "Rust"]


def test_evolution_keeps_the_ranking_fields() -> None:
    (trend,) = evolution([freq("Python", 0.62, rank=2, count=31)], [])
    assert (trend.skill, trend.norm, trend.count, trend.share, trend.rank) == (
        "Python",
        "python",
        31,
        0.62,
        2,
    )
    assert trend.new


def test_evolution_matches_on_the_normalized_name() -> None:
    current = [SkillFreq("C#", "c#", 5, 0.5, 1)]
    previous = [SkillFreq("c#", "c#", 3, 0.3, 4)]
    (trend,) = evolution(current, previous)
    assert (trend.delta_share, trend.delta_rank, trend.new) == (20, 3, False)


def test_evolution_without_previous() -> None:
    out = evolution([freq("Python", 0.62)], None)
    assert [(t.delta_share, t.delta_rank, t.new) for t in out] == [(None, None, False)]


def alerting(share: float = 0.62, name: str = "Terraform") -> list[SkillFreq]:
    return [freq(name, share)]


def test_alerts_need_ten_postings() -> None:
    assert program_alerts(alerting(1.0), 9, set(), {}) == []
    assert len(program_alerts(alerting(1.0), 10, set(), {})) == 1


def test_alerts_need_half_the_postings() -> None:
    assert program_alerts(alerting(0.49), 20, set(), {}) == []
    (alert,) = program_alerts(alerting(0.5), 20, set(), {})
    assert (alert.skill, alert.share) == ("Terraform", 0.5)


def test_alert_skips_program_and_valide() -> None:
    assert program_alerts(alerting(), 20, {"terraform"}, {}) == []  # dans un module
    levels: dict[str, SkillLevel] = {"terraform": "validated"}
    assert program_alerts(alerting(), 20, set(), levels) == []
    assert program_alerts(alerting(), 20, set(), {"terraform": "proven"}) == []
    lows: list[SkillLevel] = ["declared", "in_progress"]
    for low in lows:
        assert len(program_alerts(alerting(), 20, set(), {"terraform": low})) == 1


def test_alerts_are_capped_in_ranking_order() -> None:
    ranking = [freq(f"Skill{i}", 0.9 - i / 100, rank=i + 1) for i in range(8)]
    alerts = program_alerts(ranking, 40, set(), {})
    assert [a.skill for a in alerts] == [f"Skill{i}" for i in range(ALERT_MAX)]


def test_alert_message_wording() -> None:
    assert alert_message(0.62) == "Requested in 62% of postings and missing from your program."
    assert alert_message(0.5) == "Requested in 50% of postings and missing from your program."
    (alert,) = program_alerts(alerting(0.62), 20, set(), {})
    assert alert.message == alert_message(0.62)


def test_posting_score_uses_match_score() -> None:
    levels: dict[str, SkillLevel] = {"python": "validated"}
    rows = [{"name": "Python", "required": True}, {"name": "Docker", "required": False}]
    assert posting_score(rows, levels) == 67  # requise valide + préférée absente


def test_posting_score_reads_levels_by_normalized_name() -> None:
    levels: dict[str, SkillLevel] = {"c#": "proven", "elasticsearch": "declared"}
    rows = [
        {"name": " C# ", "required": True},
        {"name": "ElasticSearch", "required": True},
    ]
    assert posting_score(rows, levels) == 80  # (1,0 + 0,6) / 2


def test_posting_score_without_skills_is_zero() -> None:
    assert posting_score([], {"python": "validated"}) == 0
    assert posting_score([{"name": " ", "required": True}], {}) == 0


def test_posting_score_counts_a_skill_once() -> None:
    levels: dict[str, SkillLevel] = {"python": "validated"}
    rows = [
        {"name": "Python", "required": False},
        {"name": "python", "required": True},
        {"name": "Docker", "required": True},
    ]
    assert posting_score(rows, levels) == 50  # Python (requise) valide, Docker requise absente


def test_salary_shown_only_if_in_text() -> None:
    text = "Rémunération selon profil. Équipe de 5 personnes."
    assert salary_shown("45-55 k€", text) is None


def test_salary_shown_keeps_figures_found_in_the_text() -> None:
    assert salary_shown("45-55 k€", "Salaire : 45 k€ à 55 k€ brut annuel") == "45-55 k€"
    assert salary_shown("45 000 - 55 000 €", "De 45 000 € à 55 000 € par an") == "45 000 - 55 000 €"
    assert salary_shown("1,5 k€", "Prime de 1,5 k€") == "1,5 k€"


def test_salary_shown_matches_whole_numbers_only() -> None:
    assert salary_shown("45 k€", "Salaire 450 k€") is None  # 45 n'est pas 450
    assert salary_shown("45-55 k€", "Salaire 45 k€") is None  # 55 manque


def test_salary_shown_empty_or_without_figure() -> None:
    assert salary_shown(None, "45 k€") is None
    assert salary_shown("  ", "45 k€") is None
    assert salary_shown("selon profil", "selon profil, 45 k€") is None


def test_enrich_names() -> None:
    ranking = [freq("Python", 0.8), freq("SQL", 0.3), freq("Go", 0.29), freq("Rust", 0.1)]
    assert enrich_names(ranking) == ["Python", "SQL"]
    many = [freq(f"S{i}", 0.5) for i in range(20)]
    assert enrich_names(many) == [f"S{i}" for i in range(ENRICH_MAX)]
    assert enrich_names([]) == []


def test_low_sample() -> None:
    assert low_sample(29)
    assert not low_sample(30)
    assert low_sample(0)
