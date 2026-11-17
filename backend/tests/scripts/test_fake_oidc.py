import json
from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.providers.auth.base import OidcError
from app.providers.auth.google import GoogleOidc
from app.providers.auth.pkce import challenge, new_verifier
from scripts.fake_oidc import create_fake_oidc_app

ISSUER = "http://fake.invalid"
CLIENT_ID = "fake-client"
REDIRECT = "http://localhost:8000/api/v1/auth/google/callback"


@pytest.fixture
async def fake() -> AsyncIterator[httpx.AsyncClient]:
    app = create_fake_oidc_app(issuer=ISSUER, client_id=CLIENT_ID)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ISSUER, follow_redirects=False
    ) as client:
        yield client


def _provider(client: httpx.AsyncClient) -> GoogleOidc:
    return GoogleOidc(
        client_id=CLIENT_ID,
        client_secret="not-checked",
        auth_url=f"{ISSUER}/authorize",
        token_url=f"{ISSUER}/token",
        issuer=ISSUER,
        redirect_uri=REDIRECT,
        http=client,
    )


async def _authorize(
    client: httpx.AsyncClient, provider: GoogleOidc, *, verifier: str, hint: str | None = None
) -> dict[str, list[str]]:
    url = provider.authorization_url(
        state="st-1", code_challenge=challenge(verifier), nonce="n-1", login_hint=hint
    )
    response = await client.get(url)
    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == REDIRECT
    return parse_qs(location.query)


async def test_fake_oidc_full_round_trip(fake: httpx.AsyncClient) -> None:
    provider, verifier = _provider(fake), new_verifier()
    back = await _authorize(fake, provider, verifier=verifier)
    assert back["state"] == ["st-1"]
    identity = await provider.exchange(code=back["code"][0], code_verifier=verifier, nonce="n-1")
    assert identity.email == "camille.exemple@example.org"
    assert identity.email_verified is True
    assert identity.name == "Camille Exemple"
    assert identity.sub.startswith("fake-") and len(identity.sub) == len("fake-") + 16


async def test_fake_oidc_uses_login_hint_and_stable_sub(fake: httpx.AsyncClient) -> None:
    provider, subs = _provider(fake), set()
    for _ in range(2):
        verifier = new_verifier()
        back = await _authorize(
            fake, provider, verifier=verifier, hint="dominique.exemple@example.org"
        )
        identity = await provider.exchange(
            code=back["code"][0], code_verifier=verifier, nonce="n-1"
        )
        assert identity.email == "dominique.exemple@example.org"
        subs.add(identity.sub)
    assert len(subs) == 1


async def test_fake_oidc_unverified_email(fake: httpx.AsyncClient) -> None:
    provider, verifier = _provider(fake), new_verifier()
    back = await _authorize(fake, provider, verifier=verifier, hint="unverified.x@example.org")
    identity = await provider.exchange(code=back["code"][0], code_verifier=verifier, nonce="n-1")
    assert identity.email_verified is False


async def test_fake_oidc_code_single_use(fake: httpx.AsyncClient) -> None:
    provider, verifier = _provider(fake), new_verifier()
    code = (await _authorize(fake, provider, verifier=verifier))["code"][0]
    await provider.exchange(code=code, code_verifier=verifier, nonce="n-1")
    with pytest.raises(OidcError) as caught:
        await provider.exchange(code=code, code_verifier=verifier, nonce="n-1")
    assert caught.value.code == "token_invalid"


async def test_fake_oidc_rejects_wrong_verifier(fake: httpx.AsyncClient) -> None:
    provider, verifier = _provider(fake), new_verifier()
    code = (await _authorize(fake, provider, verifier=verifier))["code"][0]
    with pytest.raises(OidcError) as caught:
        await provider.exchange(code=code, code_verifier=new_verifier(), nonce="n-1")
    assert caught.value.code == "token_invalid"
    # Un code refusé est brûlé : le bon vérificateur n'y fait plus rien.
    with pytest.raises(OidcError):
        await provider.exchange(code=code, code_verifier=verifier, nonce="n-1")


async def test_fake_oidc_wrong_client_id_is_refused(fake: httpx.AsyncClient) -> None:
    other = GoogleOidc(
        client_id="someone-else",
        client_secret="x",
        auth_url=f"{ISSUER}/authorize",
        token_url=f"{ISSUER}/token",
        issuer=ISSUER,
        redirect_uri=REDIRECT,
        http=fake,
    )
    url = other.authorization_url(state="s", code_challenge="c", nonce="n", login_hint=None)
    assert (await fake.get(url)).status_code == 400


async def test_fake_oidc_requires_s256(fake: httpx.AsyncClient) -> None:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "state": "s",
        "code_challenge": "c",
        "code_challenge_method": "plain",
    }
    assert (await fake.get("/authorize", params=params)).status_code == 400


async def test_fake_oidc_deny_redirects_with_access_denied(fake: httpx.AsyncClient) -> None:
    provider = _provider(fake)
    url = provider.authorization_url(state="st-9", code_challenge="c", nonce="n", login_hint=None)
    response = await fake.get(url + "&deny=1")
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query == {"error": ["access_denied"], "state": ["st-9"]}


async def test_fake_oidc_id_token_is_unsigned(fake: httpx.AsyncClient) -> None:
    provider, verifier = _provider(fake), new_verifier()
    code = (await _authorize(fake, provider, verifier=verifier))["code"][0]
    response = await fake.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": CLIENT_ID,
            "client_secret": "x",
            "code_verifier": verifier,
        },
    )
    header, payload, signature = response.json()["id_token"].split(".")
    assert signature == ""
    pad = "=" * (-len(header) % 4)
    import base64

    assert json.loads(base64.urlsafe_b64decode(header + pad)) == {"alg": "none", "typ": "JWT"}
    assert (
        json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["iss"] == ISSUER
    )
