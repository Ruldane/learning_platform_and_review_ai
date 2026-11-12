"""Serveur de bout en bout : il ne démarre que sur un dossier de données temporaire ou dédié
(marqueur), jamais sur des données réelles, et sa base est toujours celle de ce dossier, quelle
que soit la variable `DATABASE_URL` de l'environnement."""

from pathlib import Path

import pytest

from tests.e2e.server import MARKER, UnsafeDataDir, e2e_settings, prepare_data_dir


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
