import os
from pathlib import Path

import pytest

from app.core.security import Cipher, KnownSecrets, SecretUnreadable, load_or_create_secret


def test_secret_is_created_once(tmp_path: Path) -> None:
    p = tmp_path / "secret.key"
    assert load_or_create_secret(p) == load_or_create_secret(p)


def test_secret_creates_missing_parent_dir(tmp_path: Path) -> None:
    p = tmp_path / "volume" / "secret.key"
    assert load_or_create_secret(p) and p.exists()


@pytest.mark.skipif(os.name == "nt", reason="chmod 0o600 est sans effet sous Windows")
def test_secret_file_is_private(tmp_path: Path) -> None:
    p = tmp_path / "secret.key"
    load_or_create_secret(p)
    assert p.stat().st_mode & 0o777 == 0o600


def test_roundtrip_and_wrong_secret(tmp_path: Path) -> None:
    c1 = Cipher(load_or_create_secret(tmp_path / "a"))
    c2 = Cipher(load_or_create_secret(tmp_path / "b"))
    token = c1.encrypt("sk-ant-123456")
    assert token != "sk-ant-123456" and c1.decrypt(token) == "sk-ant-123456"
    with pytest.raises(SecretUnreadable):
        c2.decrypt(token)


def test_invalid_secret_file_is_unreadable(tmp_path: Path) -> None:
    p = tmp_path / "secret.key"
    p.write_bytes(b"pas-une-cle-fernet")
    with pytest.raises(SecretUnreadable):
        Cipher(load_or_create_secret(p))


def test_known_secrets_registry_ignores_empty_and_short_values() -> None:
    KnownSecrets.add("")
    KnownSecrets.add("court")
    KnownSecrets.add("une-valeur-assez-longue")
    values = KnownSecrets.values()
    assert "" not in values and "court" not in values
    assert "une-valeur-assez-longue" in values
