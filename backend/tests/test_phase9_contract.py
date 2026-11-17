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
# Routes déjà remplies par un flux (9.B1 à 9.B5) : plus des bouchons, le contrat les liste.
FILLED: set[tuple[str, str]] = {
    ("POST", "/projects/p1/drafts"),
    ("GET", "/costs"),
    ("GET", "/costs/calls"),
    ("GET", "/settings/agents"),
    ("GET", "/account/export"),
    ("POST", "/account/delete"),
}
STUBS = [route for route in NEW_ROUTES if route[:2] not in FILLED]


def test_onboarding_done_defaults_false() -> None:
    assert UserSettings().onboarding_done is False


# Routes faites par le flux A (9.A2, 9.A3, 9.A5) : en mode local, `/auth/google/*` répond 404
# `google_auth_disabled` et `/auth/logout` 204 (voir `tests/features/auth/`) ;
# `/health/embedding` rend la progression de `bge-m3` (`tests/features/health/`).
LIVE: set[tuple[str, str]] = {
    ("GET", "/auth/google/login"),
    ("GET", "/auth/google/callback"),
    ("POST", "/auth/google/claim"),
    ("POST", "/auth/logout"),
    ("GET", "/health/embedding"),
}


def test_no_phase9_route_is_still_a_501_stub() -> None:
    """9.I : les flux A et B ont rempli tous les bouchons posés en 9.P."""
    assert [route for route in STUBS if route[:2] not in LIVE] == []


async def test_live_routes_no_longer_answer_501(client: httpx.AsyncClient) -> None:
    for method, path, body in NEW_ROUTES:
        r = await client.request(method, f"{P}{path}", json=body)
        assert r.status_code != 501, path


async def test_delete_confirmation_is_checked_in_the_code(client: httpx.AsyncClient) -> None:
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
