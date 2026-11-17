import json

import httpx
import pytest
from fastapi import FastAPI

from app.providers.auth import pkce
from tests.features.auth.support import (
    CALLBACK,
    CAMILLE,
    LOGIN,
    location_query,
    set_cookie,
    start,
)


async def test_login_redirects_with_pkce_and_sets_oauth_cookie(
    google_client: httpx.AsyncClient, google_app: FastAPI
) -> None:
    r = await start(google_client, CAMILLE)
    assert r.status_code == 302
    assert r.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    query = location_query(r)
    assert query["code_challenge_method"] == "S256" and query["login_hint"] == CAMILLE
    assert query["client_id"] == "test-client.apps.example.invalid"
    assert query["redirect_uri"] == "http://localhost:8000/api/v1/auth/google/callback"
    cookie = set_cookie(r, "tremplin_oauth")
    assert cookie is not None
    low = cookie.lower()
    assert "httponly" in low and "path=/api/v1/auth/google" in low and "max-age=600" in low
    assert "samesite=lax" in low and "; secure" not in low
    # Le témoin est chiffré ; il garde l'état du retour et le vérificateur dont `challenge` vient.
    raw = cookie.split(";")[0].split("=", 1)[1]
    pending = json.loads(google_app.state.cipher.decrypt(raw))
    assert pending["state"] == query["state"] and pending["nonce"] == query["nonce"]
    assert pkce.challenge(pending["verifier"]) == query["code_challenge"]
    assert pending["verifier"] not in r.headers["location"] and raw not in r.headers["location"]


async def test_each_login_has_its_own_state_and_nonce(google_client: httpx.AsyncClient) -> None:
    first = location_query(await start(google_client))
    second = location_query(await start(google_client))
    assert first["state"] != second["state"] and first["nonce"] != second["nonce"]
    assert len(first["state"]) >= 40 and len(first["nonce"]) >= 40


async def test_secure_cookies_when_the_return_address_is_https(
    google_client: httpx.AsyncClient, google_app: FastAPI
) -> None:
    google_app.state.settings.google_redirect_uri = "https://tremplin.example.org/cb"
    cookie = set_cookie(await start(google_client), "tremplin_oauth")
    assert cookie is not None and "; secure" in cookie.lower()


async def test_login_in_local_mode_is_404(client: httpx.AsyncClient) -> None:
    for url in (LOGIN, CALLBACK):
        r = await client.get(url, params={"code": "x", "state": "y"})
        assert r.status_code == 404 and r.json()["error"]["code"] == "google_auth_disabled"
        assert "set-cookie" not in r.headers


@pytest.mark.parametrize("hint", ["a" * 321, "pas un e-mail", "a@b", "x@y.z Set-Cookie: a=b"])
async def test_a_bad_login_hint_is_ignored_not_refused(
    google_client: httpx.AsyncClient, hint: str
) -> None:
    r = await start(google_client, hint)
    assert r.status_code == 302 and "login_hint" not in location_query(r)
    assert set_cookie(r, "tremplin_oauth") is not None


async def test_a_320_character_login_hint_is_kept(google_client: httpx.AsyncClient) -> None:
    hint = "a" * 64 + "@" + "b" * 250 + ".org"
    assert len(hint) <= 320
    assert location_query(await start(google_client, hint))["login_hint"] == hint
