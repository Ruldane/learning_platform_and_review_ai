"""Une erreur de base inattendue ne journalise aucune valeur de paramètre SQL (17.2) : contenu,
nom de fichier ou lien ne doivent jamais apparaître dans la trace du gestionnaire générique."""

import logging

import httpx
import pytest
from fastapi import FastAPI, Request
from sqlalchemy import text

PAYLOAD = "texte-confidentiel-du-document"


async def test_unexpected_db_error_logs_no_parameter_values(
    app: FastAPI, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    @app.post("/api/v1/_db_boom")
    async def db_boom(request: Request) -> None:
        async with request.app.state.session_factory() as db:
            await db.execute(text("INSERT INTO table_absente (t) VALUES (:t)"), {"t": PAYLOAD})

    caplog.set_level(logging.ERROR)
    r = await client.post("/api/v1/_db_boom")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "Erreur non gérée" in caplog.text and "OperationalError" in caplog.text
    assert PAYLOAD not in caplog.text and "hide_parameters" in caplog.text
