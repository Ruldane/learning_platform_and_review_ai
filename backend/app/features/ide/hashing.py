"""The hash of an IDE file (P9), dependency-free: schemas and services share it."""

import hashlib
import re

_HASH = re.compile(r"[0-9a-f]{64}")


def file_hash(content: str) -> str:
    """A file's hash: lowercase hexadecimal sha256 of the UTF-8 content."""
    return hashlib.sha256(content.encode()).hexdigest()


def is_file_hash(value: str | None) -> bool:
    """True for 64 lowercase hexadecimal digits."""
    return value is not None and _HASH.fullmatch(value) is not None
