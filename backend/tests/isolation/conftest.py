"""Fixtures de l'isolation : l'application en vrai mode Google (cookies de session réels), dont le
point `token` de Google est `FakeGoogle` (`httpx.MockTransport`) : aucun réseau. Chaque navigateur
a ses propres cookies ; `act_as` sert, lui, aux routeurs en mode local."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack

import httpx
import pytest
from fastapi import FastAPI

# `google` (le faux point `token`) et `google_app` (l'application en mode Google) sont ceux de la
# connexion : réimportés ici plutôt que recopiés.
from tests.features.auth.conftest import google, google_app  # noqa: F401
from tests.features.auth.support import FakeGoogle, sign_in

Browser = Callable[[str], Awaitable[httpx.AsyncClient]]


@pytest.fixture
async def google_client_factory(
    google_app: FastAPI,  # noqa: F811  (fixtures de la connexion, réimportées ci-dessus)
    google: FakeGoogle,  # noqa: F811
) -> AsyncIterator[Browser]:
    """`await browser(email)` : un nouveau navigateur (cookies à lui) connecté par le faux
    fournisseur sous cette adresse. Fermés à la fin du test."""
    async with AsyncExitStack() as stack:

        async def browser(email: str) -> httpx.AsyncClient:
            transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
            client = await stack.enter_async_context(
                httpx.AsyncClient(transport=transport, base_url="http://test")
            )
            back = await sign_in(client, google, email)
            assert back.status_code == 302 and back.headers["location"].endswith("/"), back.headers
            return client

        yield browser
