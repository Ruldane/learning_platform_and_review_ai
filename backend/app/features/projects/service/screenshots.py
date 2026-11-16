"""Les captures d'un rendu (P2) : vérifiées par leurs **octets de tête** (signature PNG, JPEG ou
WebP), jamais par le nom ni le type annoncé par le navigateur ; le suffixe rangé vient du type
détecté. Le nom du fichier reçu n'est ni gardé ni journalisé. Rangées par `FileStorage`
(`<user_id>/projects/<uuid><suffixe>`), servies avec leur type d'origine."""

import logging
from collections.abc import Sequence

from fastapi import UploadFile

from app.features.projects.service.errors import screenshot_not_found, screenshot_too_large
from app.features.projects.service.inputs import owned
from app.features.projects.service.rules import IMAGE_TYPES, SCREENSHOT_BYTES
from app.features.projects.service.runtime import STORAGE_CATEGORY, ProjectsRuntime
from app.providers.storage.base import StorageKeyInvalid

logger = logging.getLogger(__name__)

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_SUFFIX_TYPES = {suffix: media for media, suffix in IMAGE_TYPES.items()}


def detect_image(data: bytes) -> str | None:
    """Le type d'image selon les octets de tête, `None` si ce n'est ni PNG, ni JPEG, ni WebP."""
    if data.startswith(_PNG):
        return "image/png"
    if data.startswith(_JPEG):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def media_type_of(key: str) -> str:
    """Le type d'origine d'une capture rangée, d'après le suffixe de sa clé."""
    for suffix, media in _SUFFIX_TYPES.items():
        if key.endswith(suffix):
            return media
    return "application/octet-stream"


async def read_upload(file: UploadFile) -> bytes:
    """Les octets du fichier, jamais plus de 5 Mo (413 sinon) : la lecture s'arrête au plafond."""
    data = await file.read(SCREENSHOT_BYTES + 1)
    if len(data) > SCREENSHOT_BYTES:
        raise screenshot_too_large()
    return data


async def store_all(
    rt: ProjectsRuntime, user_id: str, images: Sequence[tuple[bytes, str]]
) -> list[str]:
    """Range les captures `(octets, type)` et rend leurs clés ; en cas d'échec, retire celles déjà
    rangées avant de relever l'erreur."""
    keys: list[str] = []
    try:
        for data, media in images:
            keys.append(await rt.storage.save(user_id, STORAGE_CATEGORY, data, IMAGE_TYPES[media]))
    except BaseException:
        await delete_all(rt, user_id, keys)
        raise
    return keys


async def delete_all(rt: ProjectsRuntime, user_id: str, keys: Sequence[str]) -> None:
    """Retire des captures rangées ; une panne est journalisée (classe seule), jamais relevée."""
    for key in keys:
        try:
            await rt.storage.delete(user_id, key)
        except Exception as exc:
            logger.warning("Capture non retirée : utilisateur %s (%s)", user_id, type(exc).__name__)


async def screenshot_file(
    rt: ProjectsRuntime, user_id: str, project_id: str, number: int, submission: int
) -> tuple[bytes, str]:
    """Les octets et le type d'origine de la capture `number` (à partir de 1) du rendu
    `submission` (à partir de 1, le dernier d'abord) ; 404 sinon. Le projet d'une autre : 404."""
    async with rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
    submissions = list(reversed(row.submissions))
    keys: list[str] = []
    if 1 <= submission <= len(submissions):
        keys = [str(key) for key in submissions[submission - 1].get("screenshots", [])]
    if not 1 <= number <= len(keys):
        raise screenshot_not_found()
    try:
        data = await rt.storage.read(user_id, keys[number - 1])
    except (FileNotFoundError, StorageKeyInvalid):
        raise screenshot_not_found() from None
    return data, media_type_of(keys[number - 1])
