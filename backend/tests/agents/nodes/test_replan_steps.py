"""Parcours `replan`, parties pures (D105) : droits des options, références inconnues, réponses
de January, instantané du contexte et plafond de la semaine."""

import pytest

from app.agents.nodes.strategist.replan_steps import (
    AcceptAnswer,
    as_json,
    context_from_state,
    parse_accept,
    parse_option,
    schema_for,
    to_draft,
    unknown_refs,
    without_unknown,
)
from app.agents.tools.replan_port import (
    ReplanAdds,
    ReplanDraft,
    ReplanDrops,
    ReplanSummary,
    ReplanTaskDraft,
    week_cap,
)
from app.agents.tools.study_schema import ReplanOption
from tests.support.replan import replan_context

EXTRA = ReplanTaskDraft(
    module="m9", title="Lire un article", type="lire", minutes=30, done_criterion="Notes prises"
)


@pytest.mark.parametrize(
    ("option", "schema"),
    [
        (None, ReplanSummary),
        ("push_deadline", ReplanSummary),
        ("advance", ReplanSummary),
        ("reduce_scope", ReplanDrops),
        ("deepen", ReplanAdds),
    ],
)
def test_schema_follows_option_rights(option: str | None, schema: type) -> None:
    assert schema_for(option) is schema  # type: ignore[arg-type]


def test_to_draft_keeps_only_allowed_changes() -> None:
    found = ReplanDraft(summary="x", drop=["t1", "t2", "t1"], add=[EXTRA])
    assert to_draft(found, "reduce_scope") == ReplanDraft(summary="x", drop=["t1", "t2"])
    assert to_draft(found, "deepen") == ReplanDraft(summary="x", add=[EXTRA])
    options: list[ReplanOption | None] = [None, "push_deadline", "advance"]
    for option in options:
        assert to_draft(found, option) == ReplanDraft(summary="x")


def test_unknown_refs_are_listed_then_removed() -> None:
    ctx = replan_context()
    draft = ReplanDraft(summary="x", drop=["t99", "t1"], add=[EXTRA, EXTRA.model_copy()])
    assert unknown_refs(draft, ctx) == ["t99", "m9"]
    assert without_unknown(draft, ctx) == ReplanDraft(summary="x", drop=["t1"])


def test_context_round_trips_through_state() -> None:
    ctx = replan_context("late_twice", late=2)
    assert context_from_state(as_json(ctx)) == ctx
    assert ctx.refs()["t3"] == "task-id-t3" and ctx.refs()["m1"] == "module-id-m1"


def test_parse_option() -> None:
    offered = ["reduce_scope", "push_deadline"]
    assert parse_option("reduce_scope", offered) == "reduce_scope"
    assert parse_option({"option": "push_deadline"}, offered) == "push_deadline"
    invalid: object
    for invalid in ("deepen", None, 3, {"option": "advance"}, {"answers": {}}):
        assert parse_option(invalid, offered) is None


def test_parse_accept() -> None:
    assert parse_accept("accept") == AcceptAnswer(action="accept")
    assert parse_accept({"action": "refuse", "note": "x"}) == AcceptAnswer(action="refuse")
    assert parse_accept({"answers": {"note": "  Moins  "}}) == AcceptAnswer(
        action="revise", note="Moins"
    )
    long = parse_accept({"action": "revise", "note": "a" * 3000})
    assert long is not None and len(long.note) == 2000  # coupée, jamais perdue
    invalid: object
    for invalid in ("go", None, 3, {"action": "x"}, {"answers": {"note": " "}}, {"answers": 1}):
        assert parse_accept(invalid) is None


def test_week_cap_is_exact() -> None:
    assert week_cap(300) == 255 and week_cap(60) == 51 and week_cap(10080) == 8568
