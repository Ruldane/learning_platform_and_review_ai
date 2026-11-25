import logging

import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings
from tests.features.auth.claim_support import (
    Factory,
    another_browser,
    choose,
    named,
    offered,
    seed_local_space,
)
from tests.features.auth.support import CAMILLE, DOMINIQUE, FakeGoogle, cookie_value, sign_in


@pytest.fixture
def google_settings(google_settings: Settings) -> Settings:
    return named(google_settings)


async def test_claim_never_logged(
    caplog: pytest.LogCaptureFixture,
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: Factory,
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    await seed_local_space(db_session_factory)
    first = await offered(google_client, google, CAMILLE)
    claim_cookie = cookie_value(first, "tremplin_claim")
    secrets_seen = {CAMILLE, DOMINIQUE, "Camille Exemple", "sub-camille.exemple", claim_cookie}
    assert (await choose(google_client, "take_local")).status_code == 200
    assert (await choose(google_client, "take_local")).status_code == 409  # rejeu
    async with another_browser(google_app) as second:
        await sign_in(second, google, DOMINIQUE)  # le second compte : connexion normale
    logged = "\n".join(
        record.getMessage() + " " + str(record.args) + " " + (record.exc_text or "")
        for record in caplog.records
    )
    assert "local space taken over by user" in logged  # des identifiants, rien d'autre
    for secret in secrets_seen:
        assert secret not in logged, secret
