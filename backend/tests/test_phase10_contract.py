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
    ("POST", "/ide/sessions/x1/teach", {"trigger": "run_error"}),
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
# 10.A2 : exercices, séances, exécutions, notes ; 10.A3 : génération d'exercices, professeur,
# préférences et consommation.
LIVE |= {
    ("GET", "/ide/exercises"),
    ("POST", "/ide/exercises"),
    ("DELETE", "/ide/exercises/x1"),
    ("GET", "/ide/sessions"),
    ("POST", "/ide/sessions"),
    ("GET", "/ide/sessions/x1"),
    ("PUT", "/ide/sessions/x1/files"),
    ("POST", "/ide/sessions/x1/runs"),
    ("GET", "/ide/runs/x1"),
    ("GET", "/ide/sessions/x1/notes"),
    ("POST", "/ide/sessions/x1/notes"),
    ("POST", "/ide/notes/x1/accept"),
    ("POST", "/ide/notes/x1/reject"),
    ("POST", "/ide/exercises/generate"),
    ("POST", "/ide/sessions/x1/teach"),
    ("GET", "/ide/preferences"),
    ("PUT", "/ide/preferences"),
    ("GET", "/ide/usage"),
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


def test_no_ide_route_is_a_stub_any_more() -> None:
    """10.I : le flux A a rempli toute la feature `ide` ; seuls les bouchons `mcp` restent."""
    ide = {(method, path) for method, path, _ in NEW_ROUTES if path.startswith("/ide/")}
    assert ide <= LIVE


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


def test_ide_is_an_evidence_kind() -> None:
    from typing import get_args

    assert "ide" in get_args(EvidenceKind)


def test_phase10_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.sandbox_spool_dir == Path("/spool")
    assert settings.mcp_body_limit == 1_000_000
