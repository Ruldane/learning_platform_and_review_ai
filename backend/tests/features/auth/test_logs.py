import json
import logging

import httpx
import pytest
from fastapi import FastAPI

from tests.features.auth.support import (
    CAMILLE,
    DOMINIQUE,
    FakeGoogle,
    come_back,
    location_query,
    set_cookie,
    sign_in,
    start,
)


async def test_auth_never_logged(
    caplog: pytest.LogCaptureFixture,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_app: FastAPI,
) -> None:
    # Niveau de la production pour le reste (le pilote SQLite journalise ses paramètres en DEBUG).
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    secrets_seen: set[str] = {CAMILLE, DOMINIQUE, "Camille Exemple", "sub-camille"}

    # Une connexion réussie, puis des échecs de chaque sorte.
    started = await start(google_client, CAMILLE)
    query = location_query(started)
    raw = (set_cookie(started, "tremplin_oauth") or "").split(";")[0].split("=", 1)[1]
    secrets_seen |= {
        query["state"],
        query["nonce"],
        raw,
        json.loads(google_app.state.cipher.decrypt(raw))["verifier"],
    }
    google.nonce = query["nonce"]
    ok = await come_back(google_client, code="auth-code-never-logged", state=query["state"])
    secrets_seen.add("auth-code-never-logged")
    token = (set_cookie(ok, "tremplin_session") or "").split(";")[0].split("=", 1)[1]
    secrets_seen.add(token)
    await come_back(google_client, code="other-code-never-logged", state="forged-state-0000")
    secrets_seen |= {"other-code-never-logged", "forged-state-0000"}
    google.verified = False
    await sign_in(google_client, google, DOMINIQUE)
    google.verified, google.down = True, True
    await sign_in(google_client, google, DOMINIQUE)
    google.down = False
    google.claims = {"nonce": "wrong-nonce-never-logged"}
    await sign_in(google_client, google, DOMINIQUE)
    secrets_seen.add("wrong-nonce-never-logged")
    await start(google_client, "hint-never-logged@example.org")
    secrets_seen.add("hint-never-logged@example.org")
    await google_client.get("/api/v1/auth/me", headers={"cookie": "tremplin_session=forged-0000"})
    secrets_seen.add("forged-0000")

    logged = "\n".join(
        record.getMessage() + " " + str(record.args) + " " + (record.exc_text or "")
        for record in caplog.records
    )
    for secret in secrets_seen | {"test-secret-never-logged"}:
        assert secret not in logged, secret
