"""Registre des sources d'ingestion : une source par type, titre et texte extraits."""

from datetime import date
from pathlib import Path
from typing import get_args

import pytest

from app.core.errors import AppError
from app.core.providers import MemoryProviders
from app.db.models.memory import DocumentSourceKind
from app.features.memory.service import upload
from app.features.memory.service.documents import default_paste_title
from app.features.memory.service.sources.base import ExtractionTools, SourceInput
from app.features.memory.service.sources.registry import INGESTION_SOURCES, get_source
from app.providers.web.base import Transcript, WebDocument
from scripts.sample_pdf import make_pdf
from tests.features.memory.doc_support import make_docx, make_zip
from tests.support.memory import FakeWebReader, FakeYoutube

USER = "u1"
VIDEO = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def _tools(providers: MemoryProviders) -> ExtractionTools:
    return ExtractionTools(
        storage=providers.storage, pdf=providers.pdf, web=providers.web, youtube=providers.youtube
    )


async def _extract_file(
    providers: MemoryProviders, kind: DocumentSourceKind, data: bytes, suffix: str, name: str
) -> tuple[str, str, str | None]:
    key = await providers.storage.save(USER, "documents", data, suffix)
    source = SourceInput(document_id="d1", user_id=USER, name=name, url=None, storage_key=key)
    got = await get_source(kind).extract(source, _tools(providers))
    return got.title, got.text, got.lang


def test_registry_covers_every_source_kind() -> None:
    assert set(INGESTION_SOURCES) == set(get_args(DocumentSourceKind))
    assert all(src.kind == kind for kind, src in INGESTION_SOURCES.items())


def test_unknown_source_kind_is_a_500_without_echo() -> None:
    with pytest.raises(AppError) as caught:
        get_source("exe")
    assert caught.value.code == "unknown_source_kind" and caught.value.status_code == 500
    assert "exe" not in caught.value.message


async def test_pdf_title_is_the_file_name_without_extension(
    memory_providers: MemoryProviders,
) -> None:
    title, text, lang = await _extract_file(
        memory_providers, "pdf", make_pdf(["Bonjour Tremplin"]), ".pdf", "cours.v2.pdf"
    )
    assert (title, lang) == ("cours.v2", None) and "Bonjour Tremplin" in text


async def test_docx_title_from_properties_then_heading_then_name(
    memory_providers: MemoryProviders,
) -> None:
    by_props = make_docx(["Corps du texte."], heading="Plan", core_title="Titre officiel")
    by_heading = make_docx(["Corps du texte."], heading="Plan")
    plain = make_docx(["Corps du texte."])
    assert (await _extract_file(memory_providers, "docx", by_props, ".docx", "a.docx"))[0] == (
        "Titre officiel"
    )
    title, text, _ = await _extract_file(memory_providers, "docx", by_heading, ".docx", "a.docx")
    assert title == "Plan" and "Corps du texte." in text and "Plan" in text
    assert (await _extract_file(memory_providers, "docx", plain, ".docx", "mon plan.docx"))[0] == (
        "mon plan"
    )


async def test_docx_extraction_rechecks_the_zip_guard(
    memory_providers: MemoryProviders, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Défense en profondeur : la garde zip est refaite juste avant python-docx."""
    monkeypatch.setattr(upload, "DOCX_MAX_UNCOMPRESSED", 10)
    with pytest.raises(AppError) as caught:
        await _extract_file(memory_providers, "docx", make_docx(["x"]), ".docx", "a.docx")
    assert caught.value.code == "docx_invalid"


async def test_docx_that_python_docx_cannot_open_is_invalid(
    memory_providers: MemoryProviders,
) -> None:
    broken = make_zip({"word/document.xml": b"<pas-du-docx/>"})
    with pytest.raises(AppError) as caught:
        await _extract_file(memory_providers, "docx", broken, ".docx", "a.docx")
    assert caught.value.code == "docx_invalid"


async def test_markdown_title_is_first_h1_else_name(memory_providers: MemoryProviders) -> None:
    md = b"Intro\n# Notes de cours\n\nLe *contenu*."
    title, text, _ = await _extract_file(memory_providers, "markdown", md, ".md", "n.md")
    assert title == "Notes de cours" and "Le *contenu*." in text
    other = await _extract_file(memory_providers, "markdown", b"## Sous-titre", ".md", "n.md")
    assert other[0] == "n"


async def test_text_title_is_the_name(memory_providers: MemoryProviders) -> None:
    data = "﻿Bonjour à tous".encode()
    title, text, _ = await _extract_file(memory_providers, "text", data, ".txt", "lettre.txt")
    assert (title, text) == ("lettre", "Bonjour à tous")


async def test_paste_title_is_the_document_name(memory_providers: MemoryProviders) -> None:
    title, text, _ = await _extract_file(
        memory_providers, "paste", "Texte collé ici".encode(), ".txt", "Mes notes"
    )
    assert (title, text) == ("Mes notes", "Texte collé ici")


def test_default_paste_title_is_dated() -> None:
    assert default_paste_title() == f"Texte collé du {date.today():%d/%m/%Y}"


async def test_url_title_from_page_else_host(memory_providers: MemoryProviders) -> None:
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages["https://example.org/a"] = WebDocument(
        "https://example.org/a", "Article", "Texte de la page", None, None, "fr", None
    )
    web.pages["https://example.org/b"] = WebDocument(
        "https://example.org/b", None, "Autre texte", None, None, None, None
    )
    tools = _tools(memory_providers)
    for url, expected in (
        ("https://example.org/a", ("Article", "Texte de la page", "fr")),
        ("https://example.org/b", ("example.org", "Autre texte", None)),
    ):
        src = SourceInput(document_id="d", user_id=USER, name="x", url=url, storage_key=None)
        got = await get_source("url").extract(src, tools)
        assert (got.title, got.text, got.lang) == expected
    assert web.calls[0] == ("https://example.org/a", True)


async def test_youtube_title_from_video_else_id(memory_providers: MemoryProviders) -> None:
    youtube = memory_providers.youtube
    assert isinstance(youtube, FakeYoutube)
    tools = _tools(memory_providers)
    src = SourceInput(document_id="d", user_id=USER, name="x", url=VIDEO, storage_key=None)
    youtube.videos[VIDEO] = Transcript("dQw4w9WgXcQ", "Ma vidéo", "La transcription.", True)
    got = await get_source("youtube").extract(src, tools)
    assert (got.title, got.text) == ("Ma vidéo", "La transcription.")
    youtube.videos[VIDEO] = Transcript("dQw4w9WgXcQ", None, "La transcription.", True)
    assert (await get_source("youtube").extract(src, tools)).title == "Vidéo YouTube dQw4w9WgXcQ"


async def test_file_source_reads_only_the_owner_storage(
    memory_providers: MemoryProviders, tmp_path: Path
) -> None:
    """La clé d'un autre utilisateur est refusée par le stockage (`read(user_id, key)`)."""
    key = await memory_providers.storage.save("autre", "documents", b"secret", ".txt")
    src = SourceInput(document_id="d", user_id=USER, name="x.txt", url=None, storage_key=key)
    with pytest.raises(AppError) as caught:
        await get_source("text").extract(src, _tools(memory_providers))
    assert caught.value.code == "storage_key_invalid"
