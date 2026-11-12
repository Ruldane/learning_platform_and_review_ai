import contextlib
import logging

import httpx
import pytest

from app.core.errors import AppError
from app.providers.pdf.base import RenderFailed
from app.providers.pdf.extract import PdfPlumberExtractor
from app.providers.web.base import NO_TEXT_MESSAGE, FetchedResource, UrlForbidden, UrlUnreadable
from app.providers.web.reader import TrafilaturaWebReader
from scripts.sample_pdf import make_pdf
from tests.providers.web.fetch_support import FakeResolver, fetcher_for, never, ok
from tests.support.memory import FakeRenderer

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

    async def fetch(self, url: str, **options: object) -> FetchedResource:
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


# Repli Gotenberg (D74) : page HTML sans texte principal → rendu de l'URL finale validée.

JS_PAGE = b'<html><head><title>App</title></head><body><div id="root"></div></body></html>'
RENDERED_LINES = [f"Ligne {i} du contenu rendu par le navigateur, assez longue." for i in range(8)]


def _rendering(
    renderer: FakeRenderer, content_type: str = "text/html", body: bytes | Exception = JS_PAGE
) -> TrafilaturaWebReader:
    return TrafilaturaWebReader(
        FakeFetcher(content_type, body), PdfPlumberExtractor(), renderer=renderer
    )


async def test_js_page_falls_back_to_rendered_pdf() -> None:
    renderer = FakeRenderer(make_pdf(RENDERED_LINES))
    doc = await _rendering(renderer).read(URL)
    assert "Ligne 3 du contenu rendu" in doc.text and doc.title == "App" and doc.url == URL
    [(rendered_url, timeout_s)] = renderer.calls
    assert rendered_url == URL + "?final"  # l'URL finale, validée par la garde SSRF
    assert 0 < timeout_s <= 15.0


async def test_render_fallback_never_called_for_forbidden_url() -> None:
    renderer = FakeRenderer(make_pdf(RENDERED_LINES))
    fetcher, _ = fetcher_for(never, FakeResolver({"piege.example": ["10.0.0.5"]}))
    reader = TrafilaturaWebReader(fetcher, PdfPlumberExtractor(), renderer=renderer)
    with pytest.raises(UrlForbidden):
        await reader.read("https://piege.example/vide")
    assert renderer.calls == []


@pytest.mark.parametrize(
    "response",
    [ok(b"", status=404), ok(b"\x89PNG", **{"content-type": "image/png"})],
    ids=["404", "type-refuse"],
)
async def test_render_fallback_never_called_when_fetch_failed(response: httpx.Response) -> None:
    renderer = FakeRenderer(make_pdf(RENDERED_LINES))
    fetcher, _ = fetcher_for(lambda request: response)
    reader = TrafilaturaWebReader(fetcher, PdfPlumberExtractor(), renderer=renderer)
    with pytest.raises(AppError):
        await reader.read("https://ex.org/a")
    assert renderer.calls == []


async def test_render_failure_is_unreadable(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(UrlUnreadable) as caught:
        await _rendering(FakeRenderer(RenderFailed())).read(URL)
    assert caught.value.message == NO_TEXT_MESSAGE and caught.value.__cause__ is None
    assert URL not in caplog.text


@pytest.mark.parametrize("pdf", [make_pdf(["Court."]), b"%PDF-pas un pdf"], ids=["court", "abime"])
async def test_rendered_text_still_short_or_broken_is_unreadable(pdf: bytes) -> None:
    with pytest.raises(UrlUnreadable) as caught:
        await _rendering(FakeRenderer(pdf)).read(URL)
    assert caught.value.message == NO_TEXT_MESSAGE


async def test_no_render_when_text_is_not_required() -> None:
    renderer = FakeRenderer(make_pdf(RENDERED_LINES))
    doc = await _rendering(renderer).read(URL, require_text=False)
    assert renderer.calls == [] and doc.title == "App"


@pytest.mark.parametrize(
    ("content_type", "body"),
    [("text/html", PAGE.encode()), ("text/plain", b"court"), ("application/pdf", b"%PDF-1.4")],
    ids=["html-long", "texte-court", "pdf"],
)
async def test_no_render_for_readable_html_nor_other_types(content_type: str, body: bytes) -> None:
    renderer = FakeRenderer(make_pdf(RENDERED_LINES))
    with contextlib.suppress(AppError):
        await _rendering(renderer, content_type, body).read(URL)
    assert renderer.calls == []
