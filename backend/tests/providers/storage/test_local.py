import os
import re
from pathlib import Path

import pytest

from app.providers.storage.base import StorageKeyInvalid
from app.providers.storage.local import LocalFileStorage


async def test_save_returns_key_under_user_and_category(tmp_path: Path) -> None:
    key = await LocalFileStorage(tmp_path).save("u1", "documents", b"%PDF-", ".pdf")
    assert re.fullmatch(r"u1/documents/[0-9a-f-]{36}\.pdf", key) and (tmp_path / key).is_file()


async def test_save_then_read_round_trips_and_leaves_no_temp_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = await storage.save("u1", "documents", b"bonjour", ".txt")
    assert await storage.read(key) == b"bonjour"
    assert os.listdir(tmp_path / "u1" / "documents") == [key.rsplit("/", 1)[1]]


async def test_two_saves_never_share_a_key(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    first = await storage.save("u1", "documents", b"a", ".md")
    second = await storage.save("u1", "documents", b"a", ".md")
    assert first != second


@pytest.mark.parametrize(
    "key",
    [
        "../secret.key",
        "u1/../../x",
        "/etc/passwd",
        "u1\\..\\..\\x",
        "u1/documents/../../../secret.key",
        "C:/Windows/win.ini",
        "u1/documents/x.pdf\x00.txt",
        "",
        "u1/documents",
        "u1/documents/0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.exe",
    ],
)
async def test_read_rejects_key_outside_root(tmp_path: Path, key: str) -> None:
    storage = LocalFileStorage(tmp_path / "root")
    with pytest.raises(StorageKeyInvalid) as caught:
        await storage.read(key)
    assert caught.value.code == "storage_key_invalid" and caught.value.status_code == 400
    assert caught.value.message == "Chemin de fichier refusé."
    with pytest.raises(StorageKeyInvalid):
        await storage.delete(key)


async def test_read_rejects_a_user_folder_linked_outside_root(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    (outside / "documents").mkdir(parents=True)
    name = "0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    (outside / "documents" / name).write_bytes(b"secret")
    root.mkdir()
    try:
        (root / "u1").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur ce poste")
    with pytest.raises(StorageKeyInvalid):
        await LocalFileStorage(root).read(f"u1/documents/{name}")


@pytest.mark.parametrize(
    ("user_id", "category", "suffix"),
    [
        ("u1", "documents", ".exe"),
        ("u1", "documents", ".PDF"),
        ("u1", "documents", ""),
        ("../x", "documents", ".pdf"),
        ("u1/x", "documents", ".pdf"),
        ("", "documents", ".pdf"),
        ("u" * 65, "documents", ".pdf"),
        ("u1", "Docs/", ".pdf"),
        ("u1", "..", ".pdf"),
        ("u1", "", ".pdf"),
    ],
)
async def test_save_rejects_unknown_suffix_or_unsafe_parts(
    tmp_path: Path, user_id: str, category: str, suffix: str
) -> None:
    with pytest.raises(StorageKeyInvalid):
        await LocalFileStorage(tmp_path).save(user_id, category, b"x", suffix)
    assert list(tmp_path.iterdir()) == []


async def test_delete_is_idempotent(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = await storage.save("u1", "documents", b"x", ".txt")
    await storage.delete(key)
    await storage.delete(key)
    assert not (tmp_path / key).exists()


async def test_failed_write_leaves_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_replace(src: str, dst: str) -> None:
        raise OSError("disque plein")

    monkeypatch.setattr("app.providers.storage.local.os.replace", broken_replace)
    with pytest.raises(OSError):
        await LocalFileStorage(tmp_path).save("u1", "documents", b"x", ".txt")
    assert list((tmp_path / "u1" / "documents").iterdir()) == []
