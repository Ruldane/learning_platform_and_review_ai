"""Règles pures du contrôle de fin de phase 4 : chacune échoue vraiment quand ce qu'elle
contrôle manque (sources, tours, tableau, propositions, exports)."""

from typing import Any

import pytest

from scripts.phase4_rules import (
    CheckFailed,
    check_council_events,
    check_export_files,
    debate_rounds_of,
    lessons_done,
)

DEBATERS = ("strategist", "practitioner", "scout", "skeptic")
type Events = list[dict[str, Any]]


def _turn(agent: str, step: str) -> Events:
    return [
        {"type": "agent.started", "agent": agent, "payload": {"step": step}},
        {"type": "agent.message", "agent": agent, "payload": {}},
    ]


def _sources(count: int) -> Events:
    scored = [{"source_id": f"s{n}", "score": 70} for n in range(count)]
    unscored = [{"url": "https://exemple.org", "score": None}]
    return [{"type": "source.found", "agent": "scout", "payload": p} for p in scored + unscored]


def council(
    *, sources: int = 8, rounds: int = 3, missing: str = "", boards: int = 1, proposals: int = 2
) -> Events:
    """Un Conseil fabriqué : `missing` se tait au dernier tour."""
    events = _sources(sources)
    for number in range(1, rounds + 1):
        step = "positions" if number == 1 else f"tour-{number}"
        for agent in DEBATERS:
            if not (agent == missing and number == rounds):
                events += _turn(agent, step)
    events += [{"type": "board.update", "agent": "scribe", "payload": {}}] * boards
    events += [{"type": "proposal.ready", "agent": "strategist", "payload": {}}] * proposals
    return events


def test_a_complete_council_passes() -> None:
    check_council_events(council(), debate_rounds=3)
    check_council_events(council(rounds=4, proposals=3), debate_rounds=3)


def test_rounds_are_read_from_the_debaters_steps() -> None:
    rounds = debate_rounds_of(council(rounds=2, missing="skeptic"))

    assert rounds == {1: set(DEBATERS), 2: set(DEBATERS) - {"skeptic"}}


@pytest.mark.parametrize(
    ("events", "message"),
    [
        (council(sources=7), "7 source\\(s\\) notée\\(s\\)"),
        (council(rounds=1), "1 tour\\(s\\) de débat"),
        (council(rounds=5), "5 tour\\(s\\) de débat \\(réglage : 3\\)"),
        (council(missing="skeptic"), "Tours incomplets .* \\[3\\]"),
        (council(boards=0), "Aucun tableau"),
        (council(proposals=1), "1 proposition"),
        (council(proposals=4), "4 proposition"),
    ],
)
def test_the_council_fails_when_a_rule_is_broken(events: Events, message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_council_events(events, debate_rounds=3)
    assert caught.value.step == "conseil"


def test_exports_pass_with_a_pdf_and_a_calendar() -> None:
    check_export_files(b"%PDF-1.7", "BEGIN:VCALENDAR\r\nEND:VCALENDAR")


@pytest.mark.parametrize(
    ("pdf", "ics", "message"),
    [
        (b"<html>", "BEGIN:VCALENDAR", "PDF"),
        (b"%PDF-1.7", "<html>", "calendrier"),
    ],
)
def test_exports_fail_when_a_file_is_wrong(pdf: bytes, ics: str, message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_export_files(pdf, ics)
    assert caught.value.step == "exports"


def _lesson(status: str, attempts: int, *, pdf: bool = False) -> dict[str, Any]:
    return {"id": "l1", "module_id": "m1", "status": status, "attempts": attempts,
            "pdf_available": pdf}  # fmt: skip


def test_lessons_done_waits_for_retried_failed_lesson() -> None:
    assert lessons_done([_lesson("failed", 1)], {"m1": 1}) is False
    assert lessons_done([_lesson("failed", 2)], {"m1": 1}) is False
    assert lessons_done([_lesson("ready", 2, pdf=True)], {"m1": 1}) is True


def test_lessons_done_fails_after_three_attempts() -> None:
    with pytest.raises(CheckFailed, match="l1"):
        lessons_done([_lesson("failed", 3)], {"m1": 1})
