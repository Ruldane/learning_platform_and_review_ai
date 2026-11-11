"""Suite PDF de la phase 2, jouée sur l'extracteur en thread et sur l'extracteur en
sous-processus (celui de la composition) : même comportement attendu."""

import pytest

from app.providers.pdf.base import PdfTextExtractor, PdfUnreadable
from app.providers.pdf.extract import PdfPlumberExtractor, extract_pdf_text
from app.providers.pdf.subprocess import SubprocessPdfExtractor
from scripts.sample_pdf import make_pdf


@pytest.fixture(params=["thread", "subprocess"])
def extractor(request: pytest.FixtureRequest) -> PdfTextExtractor:
    return PdfPlumberExtractor() if request.param == "thread" else SubprocessPdfExtractor()


async def test_extracts_text_of_generated_pdf(extractor: PdfTextExtractor) -> None:
    assert "Bonjour Tremplin" in await extractor.extract_text(make_pdf(["Bonjour Tremplin"]))


async def test_extracts_every_line_with_escaped_characters(extractor: PdfTextExtractor) -> None:
    text = await extractor.extract_text(make_pdf(["Ligne (une)", "back\\slash"]))
    assert "Ligne (une)" in text and "back\\slash" in text


@pytest.mark.parametrize("data", [b"", b"pas un pdf", b"%PDF-1.4\n%%EOF", b"\x00" * 64])
async def test_garbage_raises_pdf_unreadable(extractor: PdfTextExtractor, data: bytes) -> None:
    with pytest.raises(PdfUnreadable) as caught:
        await extractor.extract_text(data)
    assert caught.value.code == "pdf_unreadable" and caught.value.status_code == 422
    assert caught.value.message == "PDF illisible (protégé par mot de passe ou endommagé)."
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


async def test_text_is_capped(extractor: PdfTextExtractor, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_TEXT_CHARS", 10)
    text = await extractor.extract_text(make_pdf(["Bonjour Tremplin, une longue ligne"]))
    assert 0 < len(text) <= 10


async def test_pages_beyond_the_cap_are_ignored(
    extractor: PdfTextExtractor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_PDF_PAGES", 0)
    assert await extractor.extract_text(make_pdf(["Bonjour Tremplin"])) == ""


def test_extract_pdf_text_is_public_and_synchronous() -> None:
    assert "Bonjour" in extract_pdf_text(make_pdf(["Bonjour"]), 500, 2_000_000)
    with pytest.raises(PdfUnreadable):
        extract_pdf_text(b"pas un pdf", 500, 2_000_000)


def test_pdf_unreadable_takes_an_optional_message() -> None:
    assert PdfUnreadable("PDF trop long à lire : délai dépassé.").message.startswith("PDF trop")
