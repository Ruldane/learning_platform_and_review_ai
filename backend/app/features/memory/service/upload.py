"""Checks on imported files and links (17.2): the extension AND the content must match; a DOCX is
a zip checked against zip bombs before python-docx opens it. No message quotes the file name,
the link or the received content."""

import io
import zipfile
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import AppError
from app.features.memory.service.text import display_name
from app.providers.web.base import UrlForbidden, youtube_video_id

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PASTE_CHARS = 500_000
# Zip guard for DOCX (D66): total uncompressed size, number of entries, compression ratio
# per entry (beyond `DOCX_RATIO_FLOOR` uncompressed, a small repetitive XML quickly goes past
# 100:1 harmlessly, and the sum stays bounded by `DOCX_MAX_UNCOMPRESSED`).
DOCX_MAX_UNCOMPRESSED = 100 * 1024 * 1024
DOCX_MAX_ENTRIES = 1000
DOCX_MAX_RATIO = 100
DOCX_RATIO_FLOOR = 1024 * 1024
# XML parts (`.xml`, `.rels`) that python-docx parses with lxml: their sum is bounded separately,
# the in-memory tree weighing several times the size of the text (images stay under the
# total cap).
DOCX_MAX_XML = 25 * 1024 * 1024
DOCX_MAIN_PART = "word/document.xml"

UploadKind = Literal["pdf", "docx", "markdown", "text"]
SUFFIX_OF: dict[UploadKind, str] = {
    "pdf": ".pdf",
    "docx": ".docx",
    "markdown": ".md",
    "text": ".txt",
}
_KIND_OF_SUFFIX: dict[str, UploadKind] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
}
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"


def unsupported_file_type() -> AppError:
    return AppError(
        "unsupported_file_type",
        "Upload a PDF, DOCX, Markdown, or plain text file.",
        415,
    )


def docx_invalid() -> AppError:
    return AppError("docx_invalid", "The DOCX file is invalid or too large when decompressed.", 422)


def file_too_large() -> AppError:
    return AppError("file_too_large", "The maximum file size is 20 MB.", 413)


def _suffix(filename: str | None) -> str:
    """Extension of the cleaned name (last segment, never a path), in lowercase."""
    name = display_name(filename)
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def is_utf8_text(data: bytes) -> bool:
    """Valid UTF-8 (BOM tolerated) and without null bytes."""
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return True


def check_docx_zip(data: bytes) -> None:
    """Readable zip, `word/document.xml` present (otherwise 415), unencrypted entries, at most
    `DOCX_MAX_ENTRIES` entries, `DOCX_MAX_UNCOMPRESSED` bytes decompressed of which `DOCX_MAX_XML`
    of XML, ratio per entry bounded (otherwise `docx_invalid`). The sizes read are those of the
    central directory: `zipfile` never returns more than an entry's declared size (and checks its
    CRC)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError, EOFError):
        raise docx_invalid() from None
    if len(infos) > DOCX_MAX_ENTRIES:
        raise docx_invalid()
    if all(info.filename != DOCX_MAIN_PART for info in infos):
        raise unsupported_file_type()
    total = xml = 0
    for info in infos:
        total += info.file_size
        if info.filename.lower().endswith((".xml", ".rels")):
            xml += info.file_size
        if info.flag_bits & 0x1 or total > DOCX_MAX_UNCOMPRESSED or xml > DOCX_MAX_XML:
            raise docx_invalid()
        if info.file_size > DOCX_RATIO_FLOOR and info.file_size > DOCX_MAX_RATIO * max(
            info.compress_size, 1
        ):
            raise docx_invalid()


def detect_upload(filename: str | None, data: bytes) -> UploadKind:
    kind = _KIND_OF_SUFFIX.get(_suffix(filename))
    if kind == "pdf" and data.startswith(_PDF_MAGIC):
        return "pdf"
    if kind == "docx" and data.startswith(_ZIP_MAGIC):
        check_docx_zip(data)
        return "docx"
    if kind in ("markdown", "text") and is_utf8_text(data):
        return kind
    raise unsupported_file_type()


def classify_url(url: str) -> Literal["url", "youtube"]:
    return "youtube" if youtube_video_id(url) is not None else "url"


def invalid_url() -> AppError:
    return AppError("invalid_url", "Enter a valid HTTP or HTTPS link.", 422)


def normalize_url(url: str) -> str:
    """Scheme and host in lowercase, fragment removed; `http`/`https` with a host only, without
    credentials. The full SSRF guard remains that of the web reader, at read time."""
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise invalid_url() from None
    if parts.scheme.lower() not in ("http", "https") or not host:
        raise invalid_url()
    if parts.username is not None or parts.password is not None:
        raise UrlForbidden()
    netloc = host.lower() if ":" not in host else f"[{host.lower()}]"
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, ""))
