"""Preuves structurées d'un niveau (D99) : les chaînes de la phase 4 restent lisibles."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.skills import evidence, read_evidence


def test_evidence_is_iso_utc() -> None:
    paris = timezone(timedelta(hours=1))
    item = evidence("quiz", "q1", "Quiz Pandas : 90 %", datetime(2026, 11, 12, 10, 0, tzinfo=paris))
    assert item == {
        "kind": "quiz",
        "ref_id": "q1",
        "label": "Quiz Pandas : 90 %",
        "at": "2026-11-12T09:00:00+00:00",
    }


def test_evidence_refuses_naive_datetime() -> None:
    with pytest.raises(ValueError):
        evidence("quiz", "q1", "x", datetime(2026, 11, 12, 10, 0))


def test_read_evidence_accepts_phase4_strings() -> None:
    [item] = read_evidence(["Programme X"])
    assert item == {"kind": "program", "ref_id": None, "label": "Programme X", "at": ""}


def test_read_evidence_keeps_structured_and_drops_garbage() -> None:
    at = datetime(2026, 11, 12, tzinfo=UTC)
    good = evidence("study", "s1", "Session", at)
    raw = [good, "Ancien", 3, None, {"kind": "inconnu", "label": "x"}, {"label": "sans genre"}]
    out = read_evidence(raw)
    assert out[0] == good
    assert out[1]["label"] == "Ancien"
    assert len(out) == 2
