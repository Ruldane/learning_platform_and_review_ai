import contextlib
import os
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError

_MIN_SECRET_LENGTH = 8


class SecretUnreadable(AppError):
    """Le secret de l'application ne permet pas de lire une valeur chiffrée."""

    def __init__(self) -> None:
        super().__init__(
            "secret_unreadable",
            "La clé enregistrée est illisible : saisis-la de nouveau dans les réglages.",
            status_code=500,
        )


def load_or_create_secret(path: Path) -> bytes:
    """Relit la clé Fernet de `path`, ou la crée (droits 0o600) si le fichier n'existe pas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes().strip()
    secret = Fernet.generate_key()
    with os.fdopen(fd, "wb") as handle:
        handle.write(secret)
    # No-op sous Windows ; garantit les droits malgré l'umask ailleurs.
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    return secret


class Cipher:
    """Chiffrement symétrique (Fernet) des clés d'API stockées en base."""

    def __init__(self, secret: bytes) -> None:
        try:
            self._fernet = Fernet(secret)
        except ValueError as exc:
            raise SecretUnreadable() from exc

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise SecretUnreadable() from exc


class KnownSecrets:
    """Registre (processus entier) des valeurs à masquer dans les journaux."""

    _values: set[str] = set()
    _lock = threading.Lock()

    @classmethod
    def add(cls, value: str) -> None:
        if len(value) < _MIN_SECRET_LENGTH:
            return
        with cls._lock:
            cls._values.add(value)

    @classmethod
    def values(cls) -> frozenset[str]:
        with cls._lock:
            return frozenset(cls._values)
