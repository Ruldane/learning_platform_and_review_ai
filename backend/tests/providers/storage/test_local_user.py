"""`list_user` : les clés d'un seul utilisateur, jamais un fichier d'un autre ni un résidu."""

import os
from pathlib import Path

import pytest

from app.providers.storage.base import StorageKeyInvalid
from app.providers.storage.local import LocalFileStorage


async def test_list_user_returns_only_that_users_keys_sorted(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    mine = [
        await storage.save("u1", "documents", b"a", ".pdf"),
        await storage.save("u1", "screenshots", b"b", ".png"),
        await storage.save("u1", "documents", b"c", ".md"),
    ]
    await storage.save("u2", "documents", b"autre", ".pdf")
    await storage.save("u10", "documents", b"autre", ".pdf")  # préfixe commun, autre dossier
    assert await storage.list_user("u1") == sorted(mine)


async def test_list_user_keys_can_be_read_back(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = await storage.save("u1", "documents", b"bonjour", ".txt")
    [listed] = await storage.list_user("u1")
    assert listed == key and await storage.read("u1", listed) == b"bonjour"


async def test_list_user_without_folder_is_empty(tmp_path: Path) -> None:
    assert await LocalFileStorage(tmp_path / "absent").list_user("u1") == []
    assert await LocalFileStorage(tmp_path).list_user("u1") == []


async def test_list_user_ignores_temp_files_and_strangers(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = await storage.save("u1", "documents", b"a", ".pdf")
    folder = tmp_path / "u1" / "documents"
    (folder / ".tmp-abc.part").write_bytes(b"residu")
    (folder / "notes.txt").write_bytes(b"pas une cle generee")
    (tmp_path / "u1" / "loose.pdf").write_bytes(b"hors categorie")
    assert await storage.list_user("u1") == [key]


@pytest.mark.parametrize("user_id", ["", "../u2", "u1/documents", "u1\\x", "u\x00", "a" * 65])
async def test_list_user_rejects_a_malformed_user_id(tmp_path: Path, user_id: str) -> None:
    with pytest.raises(StorageKeyInvalid) as caught:
        await LocalFileStorage(tmp_path).list_user(user_id)
    assert caught.value.code == "storage_key_invalid"


async def test_list_user_rejects_a_user_folder_linked_outside_root(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    (outside / "documents").mkdir(parents=True)
    name = "0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    (outside / "documents" / name).write_bytes(b"secret")
    root.mkdir()
    try:
        os.symlink(outside, root / "u1", target_is_directory=True)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur cet hôte")
    with pytest.raises(StorageKeyInvalid):
        await LocalFileStorage(root).list_user("u1")


async def test_list_user_skips_a_file_linked_outside_the_user_folder(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    storage = LocalFileStorage(root)
    key = await storage.save("u1", "documents", b"a", ".pdf")
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_bytes(b"secret")
    link = root / "u1" / "documents" / "0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur cet hôte")
    assert await storage.list_user("u1") == [key]


# --- delete_user ---------------------------------------------------------------------------------


async def test_delete_user_removes_only_that_users_folder(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    mine = [
        await storage.save("u1", "documents", b"a", ".pdf"),
        await storage.save("u1", "screenshots", b"b", ".png"),
    ]
    theirs = await storage.save("u2", "documents", b"autre", ".pdf")
    longer = await storage.save("u10", "documents", b"autre", ".pdf")  # préfixe commun

    assert await storage.delete_user("u1") == len(mine)

    assert await storage.list_user("u1") == []
    assert not (tmp_path / "u1").exists()
    assert await storage.read("u2", theirs) == b"autre"
    assert await storage.read("u10", longer) == b"autre"
    for key in mine:
        with pytest.raises(FileNotFoundError):
            await storage.read("u1", key)


async def test_delete_user_is_idempotent(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.save("u1", "documents", b"a", ".pdf")
    assert await storage.delete_user("u1") == 1
    assert await storage.delete_user("u1") == 0
    assert await LocalFileStorage(tmp_path / "absent").delete_user("u1") == 0


async def test_delete_user_also_removes_residues_and_strangers(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.save("u1", "documents", b"a", ".pdf")
    folder = tmp_path / "u1" / "documents"
    (folder / ".tmp-abc.part").write_bytes(b"residu")
    (folder / "notes.txt").write_bytes(b"pas une cle generee")
    (tmp_path / "u1" / "loose.pdf").write_bytes(b"hors categorie")

    assert await storage.delete_user("u1") == 1  # seules les clés générées sont comptées

    assert not (tmp_path / "u1").exists()


async def test_the_user_folder_can_be_filled_again_after_delete(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.save("u1", "documents", b"a", ".pdf")
    await storage.delete_user("u1")
    key = await storage.save("u1", "documents", b"b", ".pdf")
    assert await storage.list_user("u1") == [key]


@pytest.mark.parametrize("user_id", ["", "../u2", "u1/documents", "u1\\x", "u\x00", "a" * 65, "."])
async def test_delete_user_rejects_a_malformed_user_id(tmp_path: Path, user_id: str) -> None:
    (tmp_path / "u2").mkdir()
    (tmp_path / "u2" / "keep.txt").write_bytes(b"reste")
    with pytest.raises(StorageKeyInvalid) as caught:
        await LocalFileStorage(tmp_path).delete_user(user_id)
    assert caught.value.code == "storage_key_invalid"
    assert (tmp_path / "u2" / "keep.txt").read_bytes() == b"reste"


async def test_delete_user_refuses_a_folder_linked_outside_root(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    (outside / "documents").mkdir(parents=True)
    secret = outside / "documents" / "0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    secret.write_bytes(b"secret")
    root.mkdir()
    try:
        os.symlink(outside, root / "u1", target_is_directory=True)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur cet hôte")
    with pytest.raises(StorageKeyInvalid):
        await LocalFileStorage(root).delete_user("u1")
    assert secret.read_bytes() == b"secret"


async def test_delete_user_unlinks_a_link_inside_without_following_it(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    storage = LocalFileStorage(root)
    await storage.save("u1", "documents", b"a", ".pdf")
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_bytes(b"secret")
    link = root / "u1" / "documents" / "0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur cet hôte")
    await storage.delete_user("u1")
    assert not (root / "u1").exists()
    assert target.read_bytes() == b"secret"


async def test_delete_user_refuses_a_folder_linked_to_another_users_folder(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    theirs = await storage.save("u2", "documents", b"autre", ".pdf")
    try:
        os.symlink(tmp_path / "u2", tmp_path / "u1", target_is_directory=True)
    except OSError:
        pytest.skip("liens symboliques indisponibles sur cet hôte")
    with pytest.raises(StorageKeyInvalid):
        await storage.delete_user("u1")
    assert await storage.read("u2", theirs) == b"autre"
