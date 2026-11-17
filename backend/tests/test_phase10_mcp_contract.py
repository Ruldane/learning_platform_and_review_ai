"""Les déclarations MCP, l'identité de l'appelant et les schémas de l'IDE (10.P, correctifs de la
relecture) : grammaire `untrusted`, `body_fields`/`merge_from`, refus, états durables."""

import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import httpx
import pytest
from pydantic import ValidationError

from app.core.caller import MCP_IDENTITY
from app.db.models.ide import IdeRun, IdeSession
from app.db.models.mcp import McpCall
from app.features.ide.schemas import (
    IdeSessionOut,
    RunOut,
    RunProgress,
    SessionSummary,
    SkipReason,
    TeachIn,
    TeachTrigger,
)
from app.features.mcp.schemas import McpCallOut
from app.features.registry import MCP_FEATURES
from app.mcp.base import (
    NEVER_EXPOSED_FEATURES,
    FeatureMcp,
    McpAction,
    McpGraph,
    untrusted_paths_valid,
)

APP = Path(__file__).resolve().parents[1] / "app"
P = "/api/v1"


def test_mcp_declarations_are_frozen_data() -> None:
    action = McpAction(route="POST /postings", level=2, name="postings_add")
    assert action.summary is None and action.side_effects == "db"
    assert action.untrusted == () and action.precheck is None
    assert action.body_fields is None and action.merge_from is None
    graph = McpGraph(graph="cv_review")
    assert graph.level == 2 and graph.untrusted == ()
    declared = FeatureMcp(feature="postings", actions=(action,), graphs=(graph,))
    assert declared.excluded == {}
    with pytest.raises(AttributeError):
        action.level = 1  # type: ignore[misc]
    assert frozenset({"auth", "account", "mcp"}) == NEVER_EXPOSED_FEATURES
    assert MCP_FEATURES == []  # 10.D1 déclare une feature par ligne


@pytest.mark.parametrize(
    "path",
    [
        "description",
        "items[].description",
        "postings[].company",
        "a.b.c",
        "a[].b[].c",
        "_x1",
        "[].title",
        "[].company.name",
        "[].items[].x",
    ],
)
def test_untrusted_paths_grammar_accepts(path: str) -> None:
    assert untrusted_paths_valid((path,)) is True


@pytest.mark.parametrize(
    "path",
    [
        "",
        "items.*.raw",
        "items[0].x",
        "Items",
        ".a",
        "a.",
        "a..b",
        "a[]]",
        "[]",
        "[]title",
        "[][].x",
        "a b",
        "1a",
        "a[].",
        "a-b",
        "a\n",
    ],
)
def test_untrusted_paths_grammar_refuses(path: str) -> None:
    assert untrusted_paths_valid((path,)) is False
    assert untrusted_paths_valid(("ok", path)) is False


def test_untrusted_paths_empty_is_valid() -> None:
    assert untrusted_paths_valid(()) is True


def test_declarations_refuse_a_bad_untrusted_path() -> None:
    with pytest.raises(ValueError):
        McpAction(route="GET /x", level=1, name="x", untrusted=("items.*.raw",))
    with pytest.raises(ValueError):
        McpGraph(graph="g", untrusted=("a..b",))
    McpAction(route="GET /x", level=1, name="x", untrusted=("items[].description", "[].title"))


def test_settings_update_preferences_is_expressible() -> None:
    action = McpAction(
        route="PUT /settings",
        name="settings_update_preferences",
        level=2,
        body_fields=frozenset({"theme", "language"}),
        merge_from="GET /settings",
    )
    assert action.body_fields == {"theme", "language"}
    assert action.merge_from == "GET /settings"
    excluded = FeatureMcp(feature="cv", excluded={"graph:cv_review": "réservé à l'interface"})
    assert "graph:cv_review" in excluded.excluded


def test_merge_from_requires_body_fields() -> None:
    with pytest.raises(ValueError):
        McpAction(route="PUT /settings", level=2, name="s", merge_from="GET /settings")
    with pytest.raises(ValueError):
        McpAction(
            route="PUT /settings",
            level=2,
            name="s",
            body_fields=frozenset({"a"}),
            merge_from="PUT /settings",
        )


def test_external_effect_cannot_be_level_two() -> None:
    with pytest.raises(ValueError):
        McpAction(route="POST /x", level=2, name="x", side_effects="external")
    McpAction(route="POST /x", level=3, name="x", side_effects="external")
    McpAction(route="GET /x", level=1, name="x", side_effects="external")


def test_only_the_mcp_dispatcher_writes_the_identity() -> None:
    offenders = [
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if path.relative_to(APP).parts[0] != "mcp"
        and re.search(r"MCP_IDENTITY\.(set|reset)\(", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
    assert MCP_IDENTITY.get() is None


def test_import_contracts_cover_mcp_and_the_sandbox_double() -> None:
    config = tomllib.loads((APP.parent / "pyproject.toml").read_text(encoding="utf-8"))
    contracts = {c["id"]: c for c in config["tool"]["importlinter"]["contracts"]}
    third = contracts["features-sans-fournisseur-concret"]
    assert "app.mcp" in third["source_modules"]
    assert "app.providers.sandbox.fake" in third["forbidden_modules"]
    assert "app.mcp" in contracts["composition-isolee"]["source_modules"]


def test_refused_calls_can_be_journaled() -> None:
    fields = {"id": "c1", "token_id": None, "action": "?", "code": 403, "duration_ms": 1}
    call = McpCallOut(**fields, level=0, ids={}, created_at=datetime.now(UTC))
    assert call.level == 0 and call.token_id is None
    assert get_args(McpCallOut.model_fields["level"].annotation) == (0, 1, 2, 3)
    assert McpCall.__table__.c.token_id.nullable is True  # type: ignore[attr-defined]
    with pytest.raises(ValidationError):
        McpCallOut(**fields, level=4, ids={}, created_at=datetime.now(UTC))


def test_teach_triggers_and_skip_reasons() -> None:
    assert set(get_args(TeachTrigger)) == {"run_error", "run_ok", "question", "hint", "idle"}
    assert set(get_args(SkipReason)) == {"cap_reached", "on_demand", "busy"}


@pytest.mark.parametrize("question", [None, "", "   \n"])
async def test_empty_question_is_422(client: httpx.AsyncClient, question: str | None) -> None:
    body = {"trigger": "question", "question": question}
    response = await client.post(f"{P}/ide/sessions/x1/teach", json=body)
    assert response.status_code == 422
    with pytest.raises(ValidationError):
        TeachIn(trigger="question", question=question)


def test_other_triggers_need_no_question() -> None:
    assert TeachIn(trigger="hint").question is None
    assert TeachIn(trigger="question", question="Pourquoi ?").question == "Pourquoi ?"


def test_durable_state_columns_and_outputs() -> None:
    assert IdeSession.__table__.c.passed_at.nullable is True  # type: ignore[attr-defined]
    signature = IdeRun.__table__.c.error_signature  # type: ignore[attr-defined]
    assert signature.nullable is True and signature.type.length == 40
    assert {"passed", "passed_at"} <= set(IdeSessionOut.model_fields)
    assert {"passed", "passed_at"} <= set(SessionSummary.model_fields)
    assert "error_signature" not in set(RunOut.model_fields) | set(RunProgress.model_fields)
    row = IdeSession(user_id="u", title="t", files={}, entry="main.py")
    assert row.passed is False
    row.passed_at = datetime.now(UTC)
    assert row.passed is True
    out = IdeSessionOut(
        id="s",
        title="t",
        exercise_id=None,
        updated_at=datetime.now(UTC),
        passed=False,
        passed_at=None,
        files={},
        entry="main.py",
    )
    assert out.passed is False
