"""Le contrat de la phase 10 (10.P) : toute la surface (routes `ide` et `mcp`, tables, port du bac
à sable, identité de l'appelant, déclarations MCP) est posée une fois ; les routes sont des
bouchons 501 `not_implemented` jusqu'à ce qu'un flux les remplisse."""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.config import Settings
from app.core.caller import MCP_IDENTITY, Caller, McpIdentity, current_caller
from app.core.skills import EvidenceKind
from app.db.base import Base
from app.db.models.mcp import McpToken
from app.features.registry import MCP_FEATURES
from app.mcp.base import NEVER_EXPOSED_FEATURES, FeatureMcp, McpAction, McpGraph
from app.providers.sandbox.base import (
    MAX_FILES,
    MAX_OUTPUT_BYTES,
    MAX_TIMEOUT_S,
    MAX_TOTAL_BYTES,
    SandboxJob,
    SandboxResult,
)
from app.providers.sandbox.fake import FakeSandbox
from tests.support.account import Archive

BACKEND = Path(__file__).resolve().parents[1]
CONTRACT = BACKEND.parent / "contracts" / "openapi.json"
P = "/api/v1"

NEW_TABLES = (
    "ide_exercises",
    "ide_sessions",
    "ide_runs",
    "ide_notes",
    "ide_preferences",
    "mcp_tokens",
    "mcp_prefs",
    "mcp_calls",
    "mcp_changes",
    "mcp_confirmations",
)

# Les 31 routes nouvelles : méthode, chemin (avec un identifiant factice), corps éventuel.
NEW_ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/ide/exercises", None),
    ("POST", "/ide/exercises", {"title": "Boucles", "statement": "Écris une boucle."}),
    ("DELETE", "/ide/exercises/x1", None),
    ("POST", "/ide/exercises/generate", {"topic": "les listes"}),
    ("GET", "/ide/sessions", None),
    ("POST", "/ide/sessions", {}),
    ("GET", "/ide/sessions/x1", None),
    ("PUT", "/ide/sessions/x1/files", {"files": {"main.py": "print(1)"}}),
    ("POST", "/ide/sessions/x1/runs", {"kind": "run"}),
    ("GET", "/ide/runs/x1", None),
    ("POST", "/ide/sessions/x1/teach", {"trigger": "run"}),
    ("GET", "/ide/sessions/x1/notes", None),
    ("POST", "/ide/sessions/x1/notes", {"kind": "annotation", "content": "À revoir."}),
    ("POST", "/ide/notes/x1/accept", None),
    ("POST", "/ide/notes/x1/reject", None),
    ("GET", "/ide/preferences", None),
    ("PUT", "/ide/preferences", {"teacher_mode": "auto"}),
    ("GET", "/ide/usage", None),
    ("GET", "/mcp/settings", None),
    ("PUT", "/mcp/settings", {"enabled": False}),
    ("GET", "/mcp/features", None),
    ("GET", "/mcp/actions", None),
    ("POST", "/mcp/tokens", {"label": "Claude Code", "features": ["postings"]}),
    ("GET", "/mcp/tokens", None),
    ("DELETE", "/mcp/tokens/x1", None),
    ("GET", "/mcp/confirmations", None),
    ("POST", "/mcp/confirmations/x1/confirm", None),
    ("POST", "/mcp/confirmations/x1/refuse", None),
    ("GET", "/mcp/calls", None),
    ("GET", "/mcp/changes", None),
    ("POST", "/mcp/changes/x1/undo", None),
]
# Routes déjà remplies par un flux (vidé à l'intégration, 10.I : plus aucun bouchon).
LIVE: set[tuple[str, str]] = set()
# 10.B1 : interrupteur, jetons et journal du MCP.
LIVE |= {
    ("GET", "/mcp/settings"),
    ("PUT", "/mcp/settings"),
    ("POST", "/mcp/tokens"),
    ("GET", "/mcp/tokens"),
    ("DELETE", "/mcp/tokens/x1"),
    ("GET", "/mcp/calls"),
}


def test_single_alembic_head() -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["0016"]
    revision = script.get_revision("0016")
    assert revision is not None and revision.down_revision == "0015"


def test_all_new_tables_have_user_id() -> None:
    for name in NEW_TABLES:
        table = Base.metadata.tables[name]
        assert "user_id" in table.c, name
        assert "id" in table.c and "created_at" in table.c, name


@pytest.mark.parametrize(("method", "path", "body"), NEW_ROUTES)
async def test_every_new_route_is_501_until_filled(
    client: httpx.AsyncClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    if (method, path) in LIVE:
        pytest.skip("route remplie par un flux")
    response = await client.request(method, f"{P}{path}", json=body)
    assert response.status_code == 501, (method, path, response.text)
    error = response.json()["error"]
    assert error["code"] == "not_implemented"


def test_contract_lists_phase10_paths() -> None:
    paths = json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"]
    patterns = [
        (re.compile(re.sub(r"\{[^}]+\}", "[^/]+", key) + "$"), item) for key, item in paths.items()
    ]
    for method, path, _ in NEW_ROUTES:
        assert any(
            regex.match(f"{P}{path}") and method.lower() in item for regex, item in patterns
        ), (method, path)


def test_caller_defaults_to_app() -> None:
    assert MCP_IDENTITY.get() is None
    assert current_caller() == Caller(kind="app", label="app")


def test_caller_reads_mcp_identity() -> None:
    identity = McpIdentity(
        user_id="u1",
        token_id="t1",
        label="Claude Code",
        features=frozenset({"postings"}),
        mode="read",
    )
    reset = MCP_IDENTITY.set(identity)
    try:
        assert current_caller() == Caller(kind="mcp", label="Claude Code")
    finally:
        MCP_IDENTITY.reset(reset)
    assert current_caller().kind == "app"


async def test_export_omits_mcp_token_hash(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me: str = app.state.local_user_id
    secret_hash = "ab" * 32
    db_session.add(
        McpToken(
            user_id=me,
            label="Claude Code",
            hash=secret_hash,
            features=["postings"],
            mode="read",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    await db_session.commit()

    response = await client.get(f"{P}/account/export")

    assert response.status_code == 200
    archive = Archive(response.content)
    rows = archive.table("mcp_tokens")
    assert [row["label"] for row in rows] == ["Claude Code"]
    assert all("hash" not in row for row in rows)
    assert secret_hash not in archive.text()


async def test_fake_sandbox_scripted() -> None:
    done = SandboxResult(status="done", exit_code=0, duration_ms=12, truncated=False)
    timeout = SandboxResult(status="timeout", exit_code=None, duration_ms=10_000, truncated=False)
    sandbox = FakeSandbox({"r1": "bonjour\n", "r2": timeout, "*": done})
    assert await sandbox.healthy() is True

    await sandbox.submit(
        SandboxJob(run_id="r1", files={"main.py": "x"}, entry="main.py", kind="run")
    )
    first = await sandbox.poll("r1", 0)
    assert first.output == "bonjour\n" and first.next_offset == len(b"bonjour\n")
    assert first.result is not None and first.result.status == "done"
    assert first.result.exit_code == 0
    rest = await sandbox.poll("r1", first.next_offset)
    assert rest.output == "" and rest.next_offset == first.next_offset
    assert (await sandbox.poll("r1", 3)).output == "jour\n"

    await sandbox.submit(
        SandboxJob(run_id="r2", files={"main.py": "x"}, entry="main.py", kind="run")
    )
    assert (await sandbox.poll("r2", 0)).result == timeout

    await sandbox.submit(
        SandboxJob(run_id="r3", files={"main.py": "x"}, entry="main.py", kind="check")
    )
    assert (await sandbox.poll("r3", 0)).result == done  # repli « * »

    await sandbox.cancel("r1")
    cancelled = (await sandbox.poll("r1", 0)).result
    assert cancelled is not None and cancelled.status == "killed"
    with pytest.raises(LookupError):
        await sandbox.poll("inconnu", 0)


async def test_fake_sandbox_truncates_and_checks_ceilings() -> None:
    sandbox = FakeSandbox({"*": "é" * MAX_OUTPUT_BYTES})
    await sandbox.submit(
        SandboxJob(run_id="big", files={"main.py": "x"}, entry="main.py", kind="run")
    )
    progress = await sandbox.poll("big", 0)
    assert progress.next_offset <= MAX_OUTPUT_BYTES
    assert progress.result is not None and progress.result.truncated is True
    too_many = {f"f{i}.py": "x" for i in range(MAX_FILES + 1)}
    with pytest.raises(ValueError):
        await sandbox.submit(SandboxJob(run_id="n", files=too_many, entry="f0.py", kind="run"))
    with pytest.raises(ValueError):
        await sandbox.submit(
            SandboxJob(
                run_id="s",
                files={"main.py": "x" * (MAX_TOTAL_BYTES + 1)},
                entry="main.py",
                kind="run",
            )
        )
    with pytest.raises(ValueError):
        await sandbox.submit(
            SandboxJob(
                run_id="t",
                files={"main.py": "x"},
                entry="main.py",
                kind="run",
                timeout_s=MAX_TIMEOUT_S + 1,
            )
        )
    with pytest.raises(ValueError):
        await sandbox.submit(
            SandboxJob(run_id="e", files={"main.py": "x"}, entry="absent.py", kind="run")
        )


def test_sandbox_job_ceilings_constants() -> None:
    assert (MAX_FILES, MAX_TOTAL_BYTES, MAX_TIMEOUT_S, MAX_OUTPUT_BYTES) == (
        20,
        200_000,
        15,
        65_536,
    )
    job = SandboxJob(run_id="r", files={}, entry="main.py", kind="run")
    assert job.timeout_s == 10


def test_mcp_declarations_are_frozen_data() -> None:
    action = McpAction(route="POST /postings", level=2, name="postings_add")
    assert action.summary is None and action.side_effects == "db"
    assert action.untrusted == () and action.precheck is None
    graph = McpGraph(graph="cv_review")
    assert graph.level == 2 and graph.untrusted == ()
    declared = FeatureMcp(feature="postings", actions=(action,), graphs=(graph,))
    assert declared.excluded == {}
    with pytest.raises(AttributeError):
        action.level = 1  # type: ignore[misc]
    assert frozenset({"auth", "account", "mcp"}) == NEVER_EXPOSED_FEATURES
    assert MCP_FEATURES == []  # 10.D1 déclare une feature par ligne


def test_ide_is_an_evidence_kind() -> None:
    from typing import get_args

    assert "ide" in get_args(EvidenceKind)


def test_phase10_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.sandbox_spool_dir == Path("/spool")
    assert settings.mcp_body_limit == 1_000_000
