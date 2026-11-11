"""Stockage sur disque local, sous `settings.storage_dir`.

Deux gardes contre la sortie du dossier : la clé doit avoir exactement la forme générée par
`save` (aucun `..`, séparateur `\\`, chemin absolu, lecteur ni octet nul ne passe), puis le chemin
résolu (liens symboliques suivis) doit rester sous la racine résolue."""

import asyncio
import os
import re
import tempfile
import uuid
from pathlib import Path

from app.providers.storage.base import ALLOWED_SUFFIXES, StorageKeyInvalid

_USER_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
_CATEGORY = re.compile(r"[a-z_]{1,32}")
_SUFFIXES = "|".join(re.escape(s) for s in ALLOWED_SUFFIXES)
_KEY = re.compile(rf"[A-Za-z0-9-]{{1,64}}/[a-z_]{{1,32}}/[0-9a-f-]{{36}}(?:{_SUFFIXES})")


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    async def save(self, user_id: str, category: str, data: bytes, suffix: str) -> str:
        if not (
            _USER_ID.fullmatch(user_id)
            and _CATEGORY.fullmatch(category)
            and suffix in ALLOWED_SUFFIXES
        ):
            raise StorageKeyInvalid()
        key = f"{user_id}/{category}/{uuid.uuid4()}{suffix}"
        await asyncio.to_thread(self._write, self._path(key), data)
        return key

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    def _path(self, key: str) -> Path:
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise StorageKeyInvalid()
        root = self._root.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root) or path == root:
            raise StorageKeyInvalid()
        return path

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        """Écriture atomique : fichier temporaire du même dossier puis `os.replace` ; en cas
        d'échec, le fichier temporaire est supprimé et la clé n'existe pas."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
