"""Détection des fichiers importés : extension ET contenu, gardes contre les bombes zip (DOCX),
classement des liens."""

import pytest

from app.core.errors import AppError
from app.features.memory.service import upload
from app.features.memory.service.upload import classify_url, detect_upload, normalize_url
from scripts.sample_pdf import make_pdf
from tests.features.memory.doc_support import make_docx, make_zip

DOCX_INVALID = "Fichier DOCX invalide ou trop volumineux une fois décompressé."
UNSUPPORTED = "Type de fichier non pris en charge : PDF, DOCX, Markdown ou texte uniquement."


def _error(filename: str | None, data: bytes) -> AppError:
    with pytest.raises(AppError) as caught:
        detect_upload(filename, data)
    return caught.value


def test_limits_are_the_documented_values() -> None:
    assert upload.MAX_UPLOAD_BYTES == 20 * 1024 * 1024
    assert upload.DOCX_MAX_UNCOMPRESSED == 100 * 1024 * 1024
    assert upload.DOCX_MAX_RATIO == 100 and upload.DOCX_MAX_ENTRIES == 1000
    assert upload.MAX_PASTE_CHARS == 500_000
    assert upload.SUFFIX_OF == {"pdf": ".pdf", "docx": ".docx", "markdown": ".md", "text": ".txt"}


def test_detect_upload_kinds() -> None:
    assert detect_upload("cours.pdf", make_pdf(["Bonjour"])) == "pdf"
    assert detect_upload("Plan.DOCX", make_docx(["Bonjour"])) == "docx"
    assert detect_upload("notes.md", "# Notes\nété".encode()) == "markdown"
    assert detect_upload("notes.markdown", b"# Notes") == "markdown"
    assert detect_upload("lisez-moi.txt", "﻿bonjour".encode()) == "text"


@pytest.mark.parametrize(
    ("filename", "data"),
    [
        ("cv.pdf", b"PK\x03\x04" + b"0" * 40),  # zip déguisé en PDF
        ("cv.docx", make_pdf(["Bonjour"])),  # PDF déguisé en DOCX
        ("cv.exe", make_pdf(["Bonjour"])),  # extension refusée, contenu PDF
        ("cv", make_pdf(["Bonjour"])),  # pas d'extension
        (None, b"bonjour"),  # pas de nom
        ("cv.docx", make_zip({"word/autre.xml": b"<x/>"})),  # zip sans word/document.xml
    ],
)
def test_extension_and_content_must_agree(filename: str | None, data: bytes) -> None:
    err = _error(filename, data)
    assert (err.code, err.status_code, err.message) == ("unsupported_file_type", 415, UNSUPPORTED)


def test_invalid_utf8_text_rejected() -> None:
    assert _error("notes.txt", b"caf\xe9").code == "unsupported_file_type"
    assert _error("notes.md", b"bonjour\x00monde").code == "unsupported_file_type"


def test_error_never_echoes_the_filename() -> None:
    err = _error("secret-dossier-medical.exe", b"x")
    assert "secret" not in err.message and err.details is None


def test_docx_zip_bomb_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plafond de la taille décompressée totale (lue dans le répertoire central, que `zipfile`
    fait respecter à la lecture)."""
    monkeypatch.setattr(upload, "DOCX_MAX_UNCOMPRESSED", 1000)
    data = make_zip({"word/document.xml": b"<w/>" * 200, "[Content_Types].xml": b"<t/>" * 100})
    err = _error("plan.docx", data)
    assert (err.code, err.status_code, err.message) == ("docx_invalid", 422, DOCX_INVALID)


def test_docx_compression_ratio_capped() -> None:
    """Une entrée de 2 Mio de zéros se compresse à ~2 Kio (taux ~1000:1) : refusée."""
    bomb = make_zip({"word/document.xml": b"<w/>", "word/media/x.bin": b"\0" * (2 * 1024 * 1024)})
    assert _error("plan.docx", bomb).code == "docx_invalid"


def test_docx_small_entries_are_exempt_from_the_ratio() -> None:
    """Sous 1 Mio décompressé, une entrée très compressible (XML répétitif) reste acceptée."""
    data = make_zip({"word/document.xml": b"<w:p/>" * 100_000})
    assert detect_upload("plan.docx", data) == "docx"


def test_docx_entry_count_capped() -> None:
    entries = {f"word/media/{i}.xml": b"x" for i in range(1000)}
    entries["word/document.xml"] = b"<w/>"
    assert _error("plan.docx", make_zip(entries, stored=True)).code == "docx_invalid"


def test_docx_truncated_zip_is_invalid() -> None:
    data = make_docx(["Bonjour"])
    assert _error("plan.docx", data[: len(data) // 2]).code == "docx_invalid"


def test_classify_url() -> None:
    assert classify_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert classify_url("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    assert classify_url("https://example.org/article") == "url"


def test_normalize_url_lowercases_scheme_and_host_and_drops_fragment() -> None:
    assert (
        normalize_url(" HTTPS://Example.ORG/Chemin?q=1#part ") == "https://example.org/Chemin?q=1"
    )


@pytest.mark.parametrize(
    "raw", ["ftp://example.org/x", "javascript:alert(1)", "https://", "pas une url", ""]
)
def test_normalize_url_rejects_non_http_without_echo(raw: str) -> None:
    with pytest.raises(AppError) as caught:
        normalize_url(raw)
    assert caught.value.code == "invalid_url" and caught.value.status_code == 422
    assert raw.strip() == "" or raw not in caught.value.message


def test_normalize_url_refuses_credentials() -> None:
    with pytest.raises(AppError) as caught:
        normalize_url("https://moi:secret@example.org/")
    assert caught.value.code == "url_forbidden" and "secret" not in caught.value.message
