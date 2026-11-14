"""Revue 6.10 (I1) : le fournisseur réel ne journalise jamais la famille (D126 : elle trahirait
la police du PDF). Transport simulé (`httpx.MockTransport`), aucun réseau."""

import httpx
import pytest

from app.providers.fonts import google
from app.providers.fonts.base import FontUnavailable
from app.providers.fonts.google import GoogleFontsSource

_TTF = b"\x00\x01\x00\x00" + b"glyphes" * 10
_FILE = "https://fonts.gstatic.com/s/carlito/v1/regular.ttf"
_CSS = (
    "@font-face {\n  font-family: 'Carlito';\n  font-style: normal;\n  font-weight: 400;\n"
    f"  src: url({_FILE}) format('truetype');\n}}"
)


def _source(file_status: int) -> GoogleFontsSource:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fonts.googleapis.com":
            return httpx.Response(200, text=_CSS)
        return httpx.Response(file_status, content=_TTF)

    return GoogleFontsSource(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _ours(caplog: pytest.LogCaptureFixture) -> str:
    return " ".join(r.getMessage() for r in caplog.records if r.name == google.__name__)


async def test_family_is_not_logged_on_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    files = await _source(200).fetch("Carlito", (400,))
    assert len(files) == 1
    assert _ours(caplog) and "Carlito" not in _ours(caplog)


async def test_family_is_not_logged_on_failure(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    with pytest.raises(FontUnavailable):
        await _source(404).fetch("Carlito", (400,))
    assert _ours(caplog) and "Carlito" not in _ours(caplog)


async def test_family_is_not_logged_on_network_error(caplog: pytest.LogCaptureFixture) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refus")

    caplog.set_level("DEBUG")
    source = GoogleFontsSource(httpx.AsyncClient(transport=httpx.MockTransport(boom)))
    with pytest.raises(FontUnavailable):
        await source.fetch("Carlito", (400,))
    assert _ours(caplog) and "Carlito" not in _ours(caplog)
