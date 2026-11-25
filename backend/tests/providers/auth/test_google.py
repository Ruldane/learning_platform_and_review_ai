import base64
import json
import logging
import time
from collections.abc import Callable
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.providers.auth.base import OidcError
from app.providers.auth.google import GoogleOidc

CLIENT_ID = "client-1.apps.example.invalid"
SECRET = "secret-value-never-logged"
NONCE = "nonce-abc"
VERIFIER = "verifier-never-logged-0123456789012345678901234567"
CODE = "code-never-logged"
ISSUER = "https://accounts.example.invalid"
REDIRECT = "http://localhost:8000/api/v1/auth/google/callback"
LONE_SURROGATE = chr(0xD800)  # `json.loads` l'accepte, `str.encode()` non


def _jwt(claims: dict[str, object]) -> str:
    def part(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'none'})}.{part(claims)}."


def _claims(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "exp": int(time.time()) + 3600,
        "nonce": NONCE,
        "sub": "sub-1",
        "email": "camille.exemple@example.org",
        "email_verified": True,
        "name": "Camille Exemple",
    }
    base.update(over)
    return base


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[GoogleOidc, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GoogleOidc(
        client_id=CLIENT_ID,
        client_secret=SECRET,
        auth_url="https://accounts.example.invalid/authorize",
        token_url="https://accounts.example.invalid/token",
        issuer=ISSUER,
        redirect_uri=REDIRECT,
        http=http,
    )
    return provider, http


def _answering(claims: dict[str, object]) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(200, json={"id_token": _jwt(claims)})


async def _exchange(handler: Callable[[httpx.Request], httpx.Response]):  # type: ignore[no-untyped-def]
    provider, http = _provider(handler)
    async with http:
        return await provider.exchange(code=CODE, code_verifier=VERIFIER, nonce=NONCE)


def test_authorization_url_has_pkce_scope_and_hint() -> None:
    provider, _ = _provider(_answering({}))
    url = provider.authorization_url(
        state="st", code_challenge="ch", nonce=NONCE, login_hint="a@example.org"
    )
    parts = urlsplit(url)
    assert (
        f"{parts.scheme}://{parts.netloc}{parts.path}"
        == "https://accounts.example.invalid/authorize"
    )
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert query == {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": "openid email profile",
        "state": "st",
        "nonce": NONCE,
        "code_challenge": "ch",
        "code_challenge_method": "S256",
        "prompt": "select_account",
        "login_hint": "a@example.org",
    }


def test_authorization_url_without_hint_has_no_login_hint() -> None:
    provider, _ = _provider(_answering({}))
    url = provider.authorization_url(state="s", code_challenge="c", nonce="n", login_hint=None)
    assert "login_hint" not in parse_qs(urlsplit(url).query)


async def test_exchange_returns_identity_and_sends_the_token_request() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id_token": _jwt(_claims())})

    identity = await _exchange(handler)
    assert (identity.sub, identity.email, identity.email_verified, identity.name) == (
        "sub-1",
        "camille.exemple@example.org",
        True,
        "Camille Exemple",
    )
    assert seen[0].method == "POST" and str(seen[0].url) == "https://accounts.example.invalid/token"
    form = {k: v[0] for k, v in parse_qs(seen[0].content.decode()).items()}
    assert form == {
        "grant_type": "authorization_code",
        "code": CODE,
        "redirect_uri": REDIRECT,
        "client_id": CLIENT_ID,
        "client_secret": SECRET,
        "code_verifier": VERIFIER,
    }
    assert seen[0].extensions["timeout"]["read"] == 10.0


async def test_issuer_without_scheme_is_accepted() -> None:
    identity = await _exchange(_answering(_claims(iss="accounts.example.invalid")))
    assert identity.sub == "sub-1"


async def test_email_verified_is_returned_as_is() -> None:
    assert (await _exchange(_answering(_claims(email_verified=False)))).email_verified is False
    # Booléen seulement : la chaîne « true » (forme de `tokeninfo`) n'est pas tolérée (M5).
    assert (await _exchange(_answering(_claims(email_verified="true")))).email_verified is False
    assert (await _exchange(_answering(_claims(email_verified="false")))).email_verified is False
    claims = _claims()
    del claims["email_verified"]
    assert (await _exchange(_answering(claims))).email_verified is False


async def test_missing_name_falls_back_to_email() -> None:
    claims = _claims()
    del claims["name"]
    assert (await _exchange(_answering(claims))).name == "camille.exemple@example.org"


@pytest.mark.parametrize(
    "over",
    [
        {"aud": "other-client"},
        {"aud": [CLIENT_ID, "other-client"]},
        {"nonce": "wrong"},
        {"nonce": None},
        {"exp": int(time.time()) - 5},
        {"exp": "soon"},
        {"exp": True},
        {"iss": "https://evil.example.invalid"},
        {"email": ""},
        {"email": 5},
        {"sub": ""},
        # Types inattendus : jamais autre chose qu'`OidcError` (I1).
        {"iss": ["https://accounts.example.invalid"]},
        {"iss": {"a": 1}},
        {"aud": {"a": 1}},
        {"aud": LONE_SURROGATE},
        {"nonce": LONE_SURROGATE},
        {"nonce": [NONCE]},
    ],
)
async def test_bad_claims_are_token_invalid(over: dict[str, object]) -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(_answering(_claims(**over)))
    assert caught.value.code == "token_invalid"


async def test_deeply_nested_claims_are_token_invalid() -> None:
    def part(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    token = f"{part(b'{}')}.{part(b'[' * 100_000 + b']' * 100_000)}."
    with pytest.raises(OidcError) as caught:
        await _exchange(lambda request: httpx.Response(200, json={"id_token": token}))
    assert caught.value.code == "token_invalid"


async def test_empty_nonce_is_refused() -> None:
    provider, http = _provider(_answering(_claims(nonce="")))
    async with http:
        with pytest.raises(OidcError) as caught:
            await provider.exchange(code=CODE, code_verifier=VERIFIER, nonce="")
    assert caught.value.code == "token_invalid"


@pytest.mark.parametrize("status", [408, 429])
async def test_temporary_refusals_are_google_unavailable(status: int) -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(lambda request: httpx.Response(status, json={"error": "slow_down"}))
    assert caught.value.code == "google_unavailable"


def test_oidc_error_accepts_only_known_codes() -> None:
    for code in ("access_denied", "google_unavailable", "token_invalid"):
        assert OidcError(code).code == code
    with pytest.raises(ValueError, match="unknown"):
        OidcError("access_dnied")


async def test_wrong_audience_is_token_invalid() -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(_answering(_claims(aud="someone-else")))
    assert caught.value.code == "token_invalid"


async def test_single_element_audience_list_is_accepted() -> None:
    assert (await _exchange(_answering(_claims(aud=[CLIENT_ID])))).sub == "sub-1"


async def test_wrong_nonce_is_token_invalid() -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(_answering(_claims(nonce="replayed")))
    assert caught.value.code == "token_invalid"


async def test_expired_id_token_is_token_invalid() -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(_answering(_claims(exp=int(time.time()) - 1)))
    assert caught.value.code == "token_invalid"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={}),
        httpx.Response(200, json={"id_token": "not-a-jwt"}),
        httpx.Response(200, json={"id_token": "a.!!!.c"}),
        httpx.Response(200, json=["id_token"]),
        httpx.Response(200, content=b"<html>"),
        httpx.Response(400, json={"error": "invalid_grant"}),
        httpx.Response(401, json={"error": "invalid_client"}),
    ],
)
async def test_unusable_answers_are_token_invalid(response: httpx.Response) -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(lambda request: response)
    assert caught.value.code == "token_invalid"


async def test_token_endpoint_500_is_google_unavailable() -> None:
    with pytest.raises(OidcError) as caught:
        await _exchange(lambda request: httpx.Response(503, text="down"))
    assert caught.value.code == "google_unavailable"


async def test_token_endpoint_timeout_is_google_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(OidcError) as caught:
        await _exchange(handler)
    assert caught.value.code == "google_unavailable"


async def test_connection_error_is_google_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(OidcError) as caught:
        await _exchange(handler)
    assert caught.value.code == "google_unavailable"


async def test_oidc_secrets_never_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    failures = [
        lambda request: httpx.Response(500, text=f"{CODE} {VERIFIER}"),
        lambda request: httpx.Response(400, json={"error": CODE}),
        _answering(_claims(nonce="wrong")),
        _answering(_claims(email="leak@example.org", aud="nobody")),
    ]
    for handler in failures:
        with pytest.raises(OidcError) as caught:
            await _exchange(handler)
        assert caught.value.code in str(caught.value)
        for secret in (CODE, VERIFIER, SECRET, "leak@example.org", "sub-1", NONCE):
            assert secret not in str(caught.value)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (CODE, VERIFIER, SECRET, "leak@example.org", "sub-1", NONCE, "wrong"):
        assert secret not in logged
