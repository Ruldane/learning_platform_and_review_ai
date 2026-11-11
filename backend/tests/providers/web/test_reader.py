import pytest

from app.providers.web.base import FetchedResource, UrlForbidden, UrlUnreadable
from app.providers.web.reader import TrafilaturaWebReader

URL = "https://example.com/guide"
ARTICLE = " ".join(["Tremplin aide à apprendre en lisant des guides complets."] * 8)
PAGE = f"""<html lang="fr"><head><title>Guide</title>
<meta name="description" content="Un guide pour apprendre.">
<meta name="author" content="Ada Lovelace"></head>
<body><nav>Accueil · Contact</nav><article><h1>Guide</h1><p>{ARTICLE}</p></article></body></html>"""


class FakeFetcher:
    def __init__(self, content_type: str, body: bytes | Exception) -> None:
        self.content_type, self.body = content_type, body
        self.calls: list[str] = []

    async def fetch(self, url: str) -> FetchedResource:
        self.calls.append(url)
        if isinstance(self.body, Exception):
            raise self.body
        return FetchedResource(url, url + "?final", self.content_type, self.body)


class FakePdf:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    async def extract_text(self, data: bytes) -> str:
        self.calls.append(data)
        return "Texte du PDF. " * 30


def _reader(content_type: str, body: bytes | Exception) -> tuple[TrafilaturaWebReader, FakePdf]:
    pdf = FakePdf()
    return TrafilaturaWebReader(FakeFetcher(content_type, body), pdf), pdf


async def test_html_main_text_and_title() -> None:
    reader, pdf = _reader("text/html", PAGE.encode())
    doc = await reader.read(URL)
    assert doc.title == "Guide" and doc.url == URL
    assert "Tremplin aide à apprendre" in doc.text and "Accueil · Contact" not in doc.text
    assert doc.description == "Un guide pour apprendre." and doc.author == "Ada Lovelace"
    assert pdf.calls == []


async def test_short_page_is_unreadable() -> None:
    reader, _ = _reader(
        "text/html", b"<html><title>Vide</title><body><p>Trop court.</p></body></html>"
    )
    with pytest.raises(UrlUnreadable) as caught:
        await reader.read(URL)
    assert caught.value.message == "Page illisible : aucun texte principal trouvé."


async def test_short_page_keeps_its_metadata_when_text_is_not_required() -> None:
    page = b'<html><head><title>Clip</title><meta name="description" content="Desc"></head></html>'
    reader, _ = _reader("text/html", page)
    doc = await reader.read(URL, require_text=False)
    assert (doc.title, doc.description) == ("Clip", "Desc") and len(doc.text) < 200


async def test_pdf_url_goes_through_pdf_extractor() -> None:
    reader, pdf = _reader("application/pdf", b"%PDF-1.4 ...")
    doc = await reader.read(URL)
    assert pdf.calls == [b"%PDF-1.4 ..."] and doc.text.startswith("Texte du PDF.")
    assert doc.title is None


@pytest.mark.parametrize("content_type", ["text/plain", "text/markdown"])
async def test_plain_text_is_decoded_with_replacement(content_type: str) -> None:
    body = ("é" * 150).encode() + b"\xff" + b" fin" * 20
    reader, _ = _reader(content_type, body)
    doc = await reader.read(URL)
    assert doc.text.startswith("é" * 150) and "�" in doc.text


async def test_text_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.providers.pdf.base.MAX_TEXT_CHARS", 250)
    reader, _ = _reader("text/plain", b"a" * 1000)
    assert len((await reader.read(URL)).text) == 250


async def test_fetch_errors_pass_through() -> None:
    reader, _ = _reader("text/html", UrlForbidden())
    with pytest.raises(UrlForbidden):
        await reader.read(URL)
