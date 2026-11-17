"""Le contrat de la phase 9 (9.P) : la surface d'API est posée une fois, les routes sont des
bouchons 501 `not_implemented` jusqu'à ce qu'un flux les remplisse, le contrat les liste."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import Response

from app.features.auth.service import cookies
from app.features.settings.schemas import UserSettings

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"
P = "/api/v1"

# Les onze routes nouvelles (`GET /auth/me` existait déjà) : méthode, chemin, corps éventuel.
NEW_ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/auth/google/login", None),
    ("GET", "/auth/google/callback", None),
    ("POST", "/auth/google/claim", {"choice": "fresh"}),
    ("POST", "/auth/logout", None),
    ("GET", "/health/embedding", None),
    ("GET", "/costs", None),
    ("GET", "/costs/calls", None),
    ("GET", "/settings/agents", None),
    ("GET", "/account/export", None),
    ("POST", "/account/delete", {"confirm": "SUPPRIMER"}),
    ("POST", "/projects/p1/drafts", None),
]


def test_onboarding_done_defaults_false() -> None:
    assert UserSettings().onboarding_done is False


# Routes déjà faites (9.A2) : en mode local, `/auth/google/*` répond 404 `google_auth_disabled`
# (voir `tests/features/auth/test_login.py`), ce ne sont plus des bouchons.
LIVE = {"/auth/google/login", "/auth/google/callback"}


@pytest.mark.parametrize(
    ("method", "path", "body"), [route for route in NEW_ROUTES if route[1] not in LIVE]
)
async def test_new_route_is_a_501_stub(
    client: httpx.AsyncClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    r = await client.request(method, f"{P}{path}", json=body)
    assert r.status_code == 501, path
    assert r.json()["error"]["code"] == "not_implemented"
    assert r.json()["error"]["message"] == "Pas encore disponible."


async def test_delete_confirmation_is_checked_before_the_stub(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{P}/account/delete", json={"confirm": "supprimer"})
    error = r.json()["error"]
    assert r.status_code == 422 and error["code"] == "confirmation_required"
    assert error["details"] == {"fields": ["confirm"]} and "supprimer" not in r.text


@pytest.mark.parametrize("days", ["0", "8", "abc", "-30"])
async def test_costs_days_must_be_7_30_or_90(client: httpx.AsyncClient, days: str) -> None:
    r = await client.get(f"{P}/costs", params={"days": days})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["days"]} and f"={days}" not in r.text


@pytest.mark.parametrize("limit", ["0", "101"])
async def test_costs_calls_limit_is_1_to_100(client: httpx.AsyncClient, limit: str) -> None:
    r = await client.get(f"{P}/costs/calls", params={"limit": limit})
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["limit"]}


async def test_claim_refuses_an_unknown_choice_without_echo(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{P}/auth/google/claim", json={"choice": "merge-everything"})
    assert r.status_code == 422 and "merge-everything" not in r.text


def test_contract_lists_phase9_paths() -> None:
    paths = json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"]
    for method, path, _ in NEW_ROUTES:
        template = path.replace("/p1/", "/{project_id}/")
        assert method.lower() in paths[f"{P}{template}"], (method, path)
    assert "get" in paths[f"{P}/auth/me"]
    assert "application/zip" in paths[f"{P}/account/export"]["get"]["responses"]["200"]["content"]
    for path in ("/auth/google/login", "/auth/google/callback"):
        assert "302" in paths[f"{P}{path}"]["get"]["responses"]


def test_auth_cookie_names_are_fixed() -> None:
    assert (cookies.SESSION_COOKIE, cookies.OAUTH_COOKIE, cookies.CLAIM_COOKIE) == (
        "tremplin_session",
        "tremplin_oauth",
        "tremplin_claim",
    )
    assert cookies.OAUTH_COOKIE_PATH == "/api/v1/auth/google"
    assert cookies.OAUTH_COOKIE_SECONDS == 600


def test_clear_session_cookie_uses_the_same_path_as_the_setting() -> None:
    response = Response()
    cookies.clear_session_cookie(response)
    header = response.headers["set-cookie"].lower()
    assert header.startswith("tremplin_session=") and "path=/" in header
    assert "max-age=0" in header and "httponly" in header and "samesite=lax" in header
