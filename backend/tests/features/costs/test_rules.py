"""Règles pures du rapport des coûts (P15) : fenêtre, jours locaux, axes, totaux."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.features.costs.service.rules import WINDOWS, CallFact, aggregate, window

PARIS = ZoneInfo("Europe/Paris")
TODAY = date(2026, 11, 16)


def fact(**over: object) -> CallFact:
    base: dict[str, object] = {
        "at": datetime(2026, 11, 15, 12, 0, tzinfo=UTC),
        "graph": "capture",
        "agent": "extractor",
        "provider": "glm",
        "model": "glm-5.3-flash",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.01,
        "estimated": False,
    }
    return CallFact(**{**base, **over})  # type: ignore[arg-type]


def test_windows_are_7_30_90() -> None:
    assert WINDOWS == (7, 30, 90)


def test_window_includes_today() -> None:
    assert window(TODAY, 7) == (date(2026, 11, 10), TODAY)
    assert window(TODAY, 30) == (date(2026, 10, 18), TODAY)


def test_by_day_has_every_day_of_window() -> None:
    since, until = window(TODAY, 30)
    report = aggregate([fact()], PARIS, since, until)
    assert report.days == 30 and (report.since, report.until) == (since, until)
    keys = [row.key for row in report.by_day]
    assert len(keys) == 30 and keys[0] == "2026-10-18" and keys[-1] == "2026-11-16"
    assert keys == sorted(keys)
    zero = next(row for row in report.by_day if row.key == "2026-11-14")
    assert (zero.calls, zero.tokens_in, zero.tokens_out, zero.cost_usd) == (0, 0, 0, 0.0)
    assert next(row for row in report.by_day if row.key == "2026-11-15").calls == 1


def test_day_is_local() -> None:
    late = fact(at=datetime(2026, 11, 15, 23, 30, tzinfo=UTC))  # 00 h 30 à Paris, le 16
    report = aggregate([late], PARIS, *window(TODAY, 7))
    assert [row.key for row in report.by_day if row.calls] == ["2026-11-16"]


def test_calls_outside_the_window_are_dropped() -> None:
    old = fact(at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC))
    report = aggregate([old, fact()], PARIS, *window(TODAY, 7))
    assert report.total.calls == 1


def test_feature_key_is_graph_or_empty() -> None:
    calls = [fact(graph="capture"), fact(graph=None), fact(graph=None, cost_usd=0.5)]
    report = aggregate(calls, PARIS, *window(TODAY, 7))
    assert [(r.key, r.calls) for r in report.by_feature] == [("", 2), ("capture", 1)]


def test_agent_key_is_agent_or_empty() -> None:
    report = aggregate([fact(agent=None), fact()], PARIS, *window(TODAY, 7))
    assert sorted(row.key for row in report.by_agent) == ["", "extractor"]


def test_model_key_is_provider_colon_model() -> None:
    report = aggregate([fact()], PARIS, *window(TODAY, 7))
    assert [row.key for row in report.by_model] == ["glm:glm-5.3-flash"]


def test_axes_sorted_by_cost_desc_then_key() -> None:
    calls = [
        fact(graph="b", cost_usd=0.1),
        fact(graph="a", cost_usd=0.1),
        fact(graph="c", cost_usd=0.3),
    ]
    report = aggregate(calls, PARIS, *window(TODAY, 7))
    assert [row.key for row in report.by_feature] == ["c", "a", "b"]


def test_estimated_calls_are_counted() -> None:
    calls = [fact(estimated=True), fact(estimated=True), fact()]
    report = aggregate(calls, PARIS, *window(TODAY, 7))
    assert report.total.estimated_calls == 2 and report.by_feature[0].estimated_calls == 2


def test_cost_is_rounded_to_six_decimals() -> None:
    calls = [fact(cost_usd=0.1234567891), fact(cost_usd=0.0000004)]
    report = aggregate(calls, PARIS, *window(TODAY, 7))
    assert report.total.cost_usd == 0.123457
    assert report.by_model[0].cost_usd == 0.123457


def test_totals_equal_sum_of_rows() -> None:
    calls = [
        fact(graph="a", agent="x", tokens_in=10, tokens_out=1, cost_usd=0.25),
        fact(graph=None, agent=None, provider="openai", model="m", tokens_in=7, cost_usd=0.5),
        fact(at=datetime(2026, 11, 12, 8, 0, tzinfo=UTC), estimated=True, cost_usd=0.125),
    ]
    report = aggregate(calls, PARIS, *window(TODAY, 7))
    for rows in (report.by_day, report.by_feature, report.by_agent, report.by_model):
        assert sum(r.calls for r in rows) == report.total.calls == 3
        assert sum(r.tokens_in for r in rows) == report.total.tokens_in == 117
        assert sum(r.tokens_out for r in rows) == report.total.tokens_out
        assert sum(r.estimated_calls for r in rows) == report.total.estimated_calls == 1
        assert sum(r.cost_usd for r in rows) == pytest.approx(report.total.cost_usd)


def test_empty_report_is_all_zero() -> None:
    report = aggregate([], PARIS, *window(TODAY, 7))
    assert report.total.calls == 0 and report.total.cost_usd == 0.0
    assert len(report.by_day) == 7 and report.by_feature == [] and report.by_model == []


def test_naive_moment_is_read_as_utc() -> None:
    naive = fact(at=datetime(2026, 11, 15, 23, 30))
    report = aggregate([naive], PARIS, *window(TODAY, 7))
    assert [row.key for row in report.by_day if row.calls] == ["2026-11-16"]
