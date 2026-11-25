"""File storage port. The received file name never enters a path: the key
is generated (`<user_id>/<category>/<uuid4><canonical suffix>`) and only it is kept."""

from typing import Protocol

from app.core.errors import AppError

# Imported documents; page images and fonts of a CV template (D119); screenshots of a project
# (PNG, JPEG, WebP: D166).
ALLOWED_SUFFIXES = (
    ".pdf",
    ".docx",
    ".md",
    ".txt",
    ".png",
    ".jpg",
    ".webp",
    ".woff2",
    ".ttf",
    ".epub",
    ".wav",
    ".html",
    ".zip",
)


class StorageKeyInvalid(AppError):
    """Key, user, category or suffix outside the expected format (or outside the root folder).
    The message never quotes the refused value."""

    def __init__(self) -> None:
        super().__init__("storage_key_invalid", "File path refused.", status_code=400)


class FileStorage(Protocol):
    async def save(self, user_id: str, category: str, data: bytes, suffix: str) -> str:
        """Writes `data` and returns the generated relative key."""
        ...

    async def read(self, user_id: str, key: str) -> bytes:
        """The key must belong to `user_id` (prefix `<user_id>/`), otherwise `StorageKeyInvalid`."""
        ...

    async def delete(self, user_id: str, key: str) -> None:
        """Idempotent: an already deleted key raises nothing. Same ownership check."""
        ...

    async def list_user(self, user_id: str) -> list[str]:
        """The keys of all the files of `user_id` (the form `save` returns, `<user_id>/`
        prefix included), sorted. Never a file of another user nor a write
        leftover; `StorageKeyInvalid` if `user_id` does not have the expected form."""
        ...

    async def delete_user(self, user_id: str) -> int:
        """Erases the whole folder of `user_id` (write leftovers included) and returns the number of
        stored files it contained. Idempotent: without a folder, returns 0. Never a file of another
        user; `StorageKeyInvalid` if `user_id` does not have the expected form or if its
        folder is a link that leaves the root."""
        ...
