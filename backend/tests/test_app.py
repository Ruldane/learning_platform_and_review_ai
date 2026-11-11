from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.main import create_app


async def test_unknown_route_uses_error_format(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_app_error_is_rendered(app: FastAPI, client: httpx.AsyncClient) -> None:
    @app.get("/api/v1/_boom")
    async def boom() -> None:
        raise AppError("demo", "Message lisible.", status_code=409, details={"k": 1})

    r = await client.get("/api/v1/_boom")
    assert r.status_code == 409
    assert r.json() == {
        "error": {"code": "demo", "message": "Message lisible.", "details": {"k": 1}}
    }


async def test_http_error_is_french_and_forwards_headers(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.get("/api/v1/_get_only")
    async def get_only() -> dict[str, bool]:
        return {"ok": True}

    r = await client.post("/api/v1/_get_only")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "http_error"
    assert r.json()["error"]["message"] == "Méthode non autorisée."
    assert "GET" in r.headers["allow"]


async def test_validation_error_is_french(app: FastAPI, client: httpx.AsyncClient) -> None:
    @app.get("/api/v1/_v")
    async def v(n: int) -> dict[str, int]:
        return {"n": n}

    r = await client.get("/api/v1/_v?n=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["message"] == "Requête invalide."


async def test_validation_error_never_echoes_the_input(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.post("/api/v1/_vbody")
    async def vbody(body: dict[str, int]) -> dict[str, int]:
        return body

    r = await client.post("/api/v1/_vbody", json={"secret": "SUPERSECRETVALUE1234"})
    assert r.status_code == 422
    assert "SUPERSECRETVALUE1234" not in r.text
    (err,) = r.json()["error"]["details"]["errors"]
    assert set(err) == {"loc", "msg", "type"} and err["loc"] == ["body", "secret"]


async def test_unhandled_error_is_500_without_trace(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.get("/api/v1/_crash")
    async def crash() -> None:
        raise RuntimeError("secret interne")

    r = await client.get("/api/v1/_crash")
    assert r.status_code == 500
    assert "secret interne" not in r.text
    assert r.json()["error"]["code"] == "internal_error"


async def test_unhandled_error_keeps_cors_headers(
    app: FastAPI, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    # Sans en-tête CORS, le navigateur masque le 500 : le front croirait le serveur injoignable.
    @app.get("/api/v1/_crash_cors")
    async def crash() -> None:
        raise RuntimeError("secret interne")

    r = await client.get("/api/v1/_crash_cors", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret interne" not in r.text
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert any(rec.getMessage() == "Erreur non gérée" for rec in caplog.records)


async def test_cors_allows_front_origin_only(client: httpx.AsyncClient) -> None:
    ok = await client.options(
        "/api/docs",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    ko = await client.options(
        "/api/docs",
        headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in ko.headers


async def test_cors_allows_loopback_twin_of_front_origin(client: httpx.AsyncClient) -> None:
    # Ports publiés sur 127.0.0.1 : l'interface peut être ouverte sous l'une ou l'autre forme.
    r = await client.get("/api/openapi.json", headers={"Origin": "http://127.0.0.1:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    other_port = await client.get("/api/openapi.json", headers={"Origin": "http://127.0.0.1:9999"})
    assert "access-control-allow-origin" not in other_port.headers


def test_cors_origins_accepts_a_list_and_adds_loopback_twins() -> None:
    s = Settings(
        _env_file=None,
        cors_origin=" http://localhost:5174/ , https://app.example.org,http://127.0.0.1:3000",
    )
    assert s.cors_origins == [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://app.example.org",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


async def test_openapi_is_served(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/openapi.json")).status_code == 200


def test_settings_derived_paths(tmp_path: Path) -> None:
    s = Settings(data_dir=tmp_path)
    assert s.checkpoints_path == s.data_dir / "checkpoints.db"
    assert s.secret_path == s.data_dir / "secret.key"
    assert s.storage_dir == s.data_dir / "storage"
    assert s.database_url is not None
    assert s.database_url.startswith("sqlite+aiosqlite:///")
    assert s.database_url.endswith("app.db")


def test_settings_explicit_database_url_wins() -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.database_url == "sqlite+aiosqlite:///:memory:"


def test_create_app_uses_passed_settings_not_cache(settings: Settings) -> None:
    assert create_app(settings).state.settings is settings
    assert get_settings() is not settings
