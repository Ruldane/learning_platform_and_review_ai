"""The screenshots of a submission (P2): checked by their **leading bytes** (PNG, JPEG or WebP
signature), never by the name or the type announced by the browser; the stored suffix comes
from the detected type. The received file name is neither kept nor logged. Stored by
`FileStorage` (`<user_id>/projects/<uuid><suffix>`), served with their original type."""

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


def _is_jpeg(data: bytes) -> bool:
    """`FF D8 FF` followed by a marker byte (`C0` to `FE`: APPn, DQT, DHT, SOFn, COM...) and the
    segment length on two bytes: a file reduced to the signature, or to the bare signature and
    marker (4 bytes), is not an image (D181)."""
    return len(data) >= 6 and data.startswith(_JPEG) and 0xC0 <= data[3] <= 0xFE


def detect_image(data: bytes) -> str | None:
    """The image type according to the leading bytes, `None` if it is neither PNG, JPEG nor WebP."""
    if data.startswith(_PNG):
        return "image/png"
    if _is_jpeg(data):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def media_type_of(key: str) -> str:
    """The original type of a stored screenshot, from the suffix of its key."""
    for suffix, media in _SUFFIX_TYPES.items():
        if key.endswith(suffix):
            return media
    return "application/octet-stream"


async def read_upload(file: UploadFile) -> bytes:
    """The file's bytes, never more than 5 MB (413 otherwise): reading stops at the cap."""
    data = await file.read(SCREENSHOT_BYTES + 1)
    if len(data) > SCREENSHOT_BYTES:
        raise screenshot_too_large()
    return data


async def store_all(
    rt: ProjectsRuntime, user_id: str, images: Sequence[tuple[bytes, str]]
) -> list[str]:
    """Stores the `(bytes, type)` screenshots and returns their keys; on failure, removes those
    already stored before raising the error."""
    keys: list[str] = []
    try:
        for data, media in images:
            keys.append(await rt.storage.save(user_id, STORAGE_CATEGORY, data, IMAGE_TYPES[media]))
    except BaseException:
        await delete_all(rt, user_id, keys)
        raise
    return keys


async def delete_all(rt: ProjectsRuntime, user_id: str, keys: Sequence[str]) -> None:
    """Removes stored screenshots; a failure is logged (class only), never raised."""
    for key in keys:
        try:
            await rt.storage.delete(user_id, key)
        except Exception as exc:
            logger.warning("Screenshot not removed: user %s (%s)", user_id, type(exc).__name__)


async def screenshot_file(
    rt: ProjectsRuntime, user_id: str, project_id: str, number: int, submission: int
) -> tuple[bytes, str]:
    """The bytes and original type of screenshot `number` (from 1) of submission `submission`
    (from 1, the latest first); 404 otherwise. Another user's project: 404."""
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
