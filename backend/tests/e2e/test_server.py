"""Serveur de bout en bout : il ne démarre que sur un dossier de données temporaire ou dédié
(marqueur), jamais sur des données réelles, et sa base est toujours celle de ce dossier, quelle
que soit la variable `DATABASE_URL` de l'environnement."""

import asyncio
import socket
from pathlib import Path

import httpx
import pytest
import uvicorn

from tests.e2e.server import (
    MARKER,
    UnsafeDataDir,
    UnsafeHost,
    build_app,
    check_host,
    e2e_settings,
    main,
    migrate,
    prepare_data_dir,
)

ALICE = "camille.exemple@example.org"


def test_a_new_temporary_dir_is_created_and_marked(tmp_path: Path) -> None:
    data_dir = prepare_data_dir(tmp_path / "e2e" / "1")

    assert data_dir.is_dir()
    assert (data_dir / MARKER).is_file()


def test_a_marked_dir_outside_the_temporary_dir_is_accepted(tmp_path: Path) -> None:
    dedicated = tmp_path / "dedie"
    dedicated.mkdir()
    (dedicated / MARKER).touch()

    assert prepare_data_dir(dedicated, temp_root=tmp_path / "ailleurs") == dedicated.resolve()


def test_an_unmarked_dir_outside_the_temporary_dir_is_refused(tmp_path: Path) -> None:
    with pytest.raises(UnsafeDataDir, match="ni temporaire ni dédié"):
        prepare_data_dir(tmp_path / "data", temp_root=tmp_path / "ailleurs")
    assert not (tmp_path / "data").exists()


def test_the_repository_data_dir_is_refused() -> None:
    repository_data = Path(__file__).resolve().parents[2] / "data"

    with pytest.raises(UnsafeDataDir):
        prepare_data_dir(repository_data, temp_root=Path("/nulle-part"))


def test_a_non_empty_unmarked_dir_is_refused(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("à garder", encoding="utf-8")

    with pytest.raises(UnsafeDataDir, match="non vide"):
        prepare_data_dir(tmp_path)


def test_a_used_dir_is_refused_even_when_marked(tmp_path: Path) -> None:
    (tmp_path / MARKER).touch()
    (tmp_path / "app.db").touch()

    with pytest.raises(UnsafeDataDir, match="déjà une base"):
        prepare_data_dir(tmp_path)


def test_the_database_lives_in_the_data_dir_whatever_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:////donnees/reelles/app.db")

    settings = e2e_settings(tmp_path, origin="http://localhost:5180")

    assert settings.database_url == f"sqlite+aiosqlite:///{(tmp_path / 'app.db').as_posix()}"
    assert settings.data_dir == tmp_path
    assert settings.scheduler_enabled is False


def test_google_settings_point_at_the_fake_provider_of_the_server(tmp_path: Path) -> None:
    settings = e2e_settings(tmp_path, origin="http://localhost:5180", auth="google", port=8123)

    base = "http://localhost:8123"
    assert settings.auth_mode == "google" and settings.allowed_emails == "*"
    assert settings.google_auth_url == f"{base}/fake-oidc/authorize"
    assert settings.google_token_url == f"{base}/fake-oidc/token"
    assert settings.google_issuer == f"{base}/fake-oidc"
    assert settings.google_redirect_uri == f"{base}/api/v1/auth/google/callback"
    assert settings.frontend_url == "http://localhost:5180"
    assert settings.google_client_id == "fake-client" and settings.scheduler_enabled is False


def test_local_settings_stay_in_local_mode(tmp_path: Path) -> None:
    assert e2e_settings(tmp_path, origin="http://localhost:5180").auth_mode == "local"


async def test_e2e_server_google_mode_round_trip(tmp_path: Path) -> None:
    """Le serveur en `--auth google`, en vrai HTTP : connexion → faux fournisseur → cookie."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    data_dir = prepare_data_dir(tmp_path / "e2e-google")
    settings = e2e_settings(data_dir, origin="http://localhost:5180", auth="google", port=port)
    await asyncio.to_thread(migrate, settings)  # `env.py` d'Alembic lance sa propre boucle
    server = uvicorn.Server(uvicorn.Config(build_app(settings), log_level="warning"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    base = f"http://localhost:{port}"
    try:
        async with asyncio.timeout(60):
            while not server.started:
                if task.done():
                    task.result()
                await asyncio.sleep(0.05)
        async with httpx.AsyncClient(base_url=base, follow_redirects=False) as client:
            assert (await client.get("/api/v1/auth/me")).status_code == 401
            start = await client.get("/api/v1/auth/google/login", params={"login_hint": ALICE})
            assert start.status_code == 302
            assert start.headers["location"].startswith(f"{base}/fake-oidc/authorize?")
            authorized = await client.get(start.headers["location"])  # le faux fournisseur
            assert authorized.headers["location"].startswith(f"{base}/api/v1/auth/google/callback")
            back = await client.get(authorized.headers["location"])  # échange du code, en vrai
            assert back.status_code == 302
            assert back.headers["location"] == "http://localhost:5180/"
            assert "tremplin_session=" in back.headers["set-cookie"]
            me = (await client.get("/api/v1/auth/me")).json()
            assert me["email"] == ALICE and me["auth_mode"] == "google"
            assert (await client.get("/api/v1/health")).status_code == 200
            assert (await client.post("/api/v1/auth/logout")).status_code == 204
            assert (await client.get("/api/v1/auth/me")).status_code == 401
    finally:
        server.should_exit = True
        await task
        sock.close()


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_google_mode_accepts_loopback_hosts(host: str) -> None:
    check_host(host, "google")


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.org", "::", ""])
def test_google_mode_refuses_a_host_that_is_not_loopback(host: str) -> None:
    with pytest.raises(UnsafeHost, match="127.0.0.1"):
        check_host(host, "google")


def test_local_mode_keeps_any_host() -> None:
    check_host("0.0.0.0", "local")


def test_main_refuses_google_on_a_public_host_before_touching_anything(tmp_path: Path) -> None:
    data_dir = tmp_path / "e2e-refused"
    with pytest.raises(SystemExit) as exit_info:
        main(["--auth", "google", "--host", "0.0.0.0", "--data-dir", str(data_dir)])
    assert "127.0.0.1" in str(exit_info.value)
    assert not data_dir.exists()  # aucun dossier créé, aucune base
