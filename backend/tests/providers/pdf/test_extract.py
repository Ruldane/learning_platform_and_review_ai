import pytest

from app.providers.pdf.base import PdfUnreadable
from app.providers.pdf.extract import PdfPlumberExtractor
from scripts.sample_pdf import make_pdf


async def test_extracts_text_of_generated_pdf() -> None:
    assert "Bonjour Tremplin" in await PdfPlumberExtractor().extract_text(
        make_pdf(["Bonjour Tremplin"])
    )


async def test_extracts_every_line_with_escaped_characters() -> None:
    text = await PdfPlumberExtractor().extract_text(make_pdf(["Ligne (une)", "back\\slash"]))
    assert "Ligne (une)" in text and "back\\slash" in text


@pytest.mark.parametrize("data", [b"", b"pas un pdf", b"%PDF-1.4\n%%EOF", b"\x00" * 64])
async def test_garbage_raises_pdf_unreadable(data: bytes) -> None:
    with pytest.raises(PdfUnreadable) as caught:
        await PdfPlumberExtractor().extract_text(data)
    assert caught.value.code == "pdf_unreadable" and caught.value.status_code == 422
    assert caught.value.message == "PDF illisible (protégé par mot de passe ou endommagé)."
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


async def test_text_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_TEXT_CHARS", 10)
    text = await PdfPlumberExtractor().extract_text(
        make_pdf(["Bonjour Tremplin, une longue ligne"])
    )
    assert 0 < len(text) <= 10


async def test_pages_beyond_the_cap_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_PDF_PAGES", 0)
    assert await PdfPlumberExtractor().extract_text(make_pdf(["Bonjour Tremplin"])) == ""
