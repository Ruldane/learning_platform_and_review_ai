import contextlib
import os
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import AppError

_MIN_SECRET_LENGTH = 8


class SecretUnreadable(AppError):
    """The application secret cannot read an encrypted value."""

    def __init__(self) -> None:
        super().__init__(
            "secret_unreadable",
            "The saved key is unreadable: enter it again in the settings.",
            status_code=500,
        )


def load_or_create_secret(path: Path) -> bytes:
    """Reads the Fernet key of `path`, or creates it (mode 0o600) if the file does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes().strip()
    secret = Fernet.generate_key()
    with os.fdopen(fd, "wb") as handle:
        handle.write(secret)
    # No-op on Windows; guarantees the rights despite the umask elsewhere.
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    return secret


class Cipher:
    """Symmetric encryption (Fernet) of the API keys stored in the database."""

    def __init__(self, secret: bytes) -> None:
        try:
            self._fernet = Fernet(secret)
        except ValueError as exc:
            raise SecretUnreadable() from exc

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()

    def decrypt(self, token: str, *, ttl: int | None = None) -> str:
        """Decrypts `token`; with `ttl` (seconds), an older token is refused like an
        unreadable one (sign-in witnesses, valid for 10 minutes)."""
        try:
            return self._fernet.decrypt(token.encode(), ttl=ttl).decode()
        except InvalidToken as exc:
            raise SecretUnreadable() from exc


class KnownSecrets:
    """Registry (whole process) of the values to mask in the logs."""

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
