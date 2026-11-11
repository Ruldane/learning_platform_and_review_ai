"""Contrôle des fichiers et liens importés (17.2) : l'extension ET le contenu doivent concorder ;
un DOCX est un zip vérifié contre les bombes avant que python-docx ne l'ouvre. Aucun message
ne cite le nom du fichier, le lien ni le contenu reçus."""

import io
import zipfile
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import AppError
from app.features.memory.service.text import display_name
from app.providers.web.base import UrlForbidden, youtube_video_id

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PASTE_CHARS = 500_000
# Garde zip des DOCX (D66) : taille décompressée totale, nombre d'entrées, taux de compression
# par entrée (au-delà de `DOCX_RATIO_FLOOR` décompressés : un petit XML répétitif dépasse vite
# 100:1 sans danger, et la somme reste bornée par `DOCX_MAX_UNCOMPRESSED`).
DOCX_MAX_UNCOMPRESSED = 100 * 1024 * 1024
DOCX_MAX_ENTRIES = 1000
DOCX_MAX_RATIO = 100
DOCX_RATIO_FLOOR = 1024 * 1024
# Parties XML (`.xml`, `.rels`) que python-docx analyse avec lxml : leur somme est bornée à part,
# l'arbre en mémoire pesant plusieurs fois la taille du texte (les images restent sous le plafond
# total).
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
        "Type de fichier non pris en charge : PDF, DOCX, Markdown ou texte uniquement.",
        415,
    )


def docx_invalid() -> AppError:
    return AppError(
        "docx_invalid", "Fichier DOCX invalide ou trop volumineux une fois décompressé.", 422
    )


def file_too_large() -> AppError:
    return AppError("file_too_large", "Fichier trop volumineux : 20 Mo au maximum.", 413)


def _suffix(filename: str | None) -> str:
    """Extension du nom nettoyé (dernier segment, jamais un chemin), en minuscules."""
    name = display_name(filename)
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def is_utf8_text(data: bytes) -> bool:
    """UTF-8 valide (BOM toléré) et sans octet nul."""
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return True


def check_docx_zip(data: bytes) -> None:
    """Zip lisible, `word/document.xml` présent (sinon 415), entrées non chiffrées, au plus
    `DOCX_MAX_ENTRIES` entrées, `DOCX_MAX_UNCOMPRESSED` octets décompressés dont `DOCX_MAX_XML`
    de XML, taux par entrée
    borné (sinon `docx_invalid`). Les tailles lues sont celles du répertoire central : `zipfile`
    ne rend jamais plus que la taille déclarée d'une entrée (et vérifie son CRC)."""
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
    return AppError("invalid_url", "Lien invalide : une adresse http(s) est attendue.", 422)


def normalize_url(url: str) -> str:
    """Schéma et hôte en minuscules, fragment retiré ; `http`/`https` avec un hôte seulement,
    sans identifiants. La garde SSRF complète reste celle du lecteur web, à la lecture."""
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
