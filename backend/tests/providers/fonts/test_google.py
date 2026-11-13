"""Polices de Google Fonts (D119), sans réseau (respx) : deux hôtes seulement, plafonds, refus
lisibles, journal sans adresse."""

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.providers.fonts import google
from app.providers.fonts.base import FONT_MAX_BYTES, FontUnavailable
from app.providers.fonts.google import GoogleFontsSource, fonts_http

_TTF = b"\x00\x01\x00\x00" + b"glyphes" * 10
_CSS_ROUTE = "https://fonts.googleapis.com/css2"


def _css(*faces: tuple[int, str, str]) -> str:
    return "\n".join(
        f"@font-face {{\n  font-family: 'X';\n  font-style: {style};\n  font-weight: {weight};\n"
        f"  src: url({url}) format('truetype');\n}}"
        for weight, style, url in faces
    )


_LATO = _css(
    (400, "normal", "https://fonts.gstatic.com/s/lato/v25/regular.ttf"),
    (700, "normal", "https://fonts.gstatic.com/s/lato/v25/bold.ttf"),
)


@pytest.fixture
async def source() -> AsyncIterator[GoogleFontsSource]:
    async with fonts_http() as http:
        yield GoogleFontsSource(http)


async def test_google_source_fetches_only_two_hosts(
    respx_mock: respx.MockRouter, source: GoogleFontsSource
) -> None:
    css = respx_mock.get(_CSS_ROUTE).respond(200, text=_LATO)
    regular = respx_mock.get("https://fonts.gstatic.com/s/lato/v25/regular.ttf").respond(
        200, content=_TTF
    )
    bold = respx_mock.get("https://fonts.gstatic.com/s/lato/v25/bold.ttf").respond(
        200, content=_TTF + b"!"
    )
    files = await source.fetch("Lato")
    assert [(f.family, f.weight, f.style, f.suffix) for f in files] == [
        ("Lato", 400, "normal", ".ttf"),
        ("Lato", 700, "normal", ".ttf"),
    ]
    assert files[1].data == _TTF + b"!" and regular.called and bold.called
    request = css.calls.last.request
    assert request.url.params["family"] == "Lato:wght@400;700"
    assert request.headers["user-agent"] == "Tremplin"


async def test_other_host_in_css_is_refused(
    respx_mock: respx.MockRouter, source: GoogleFontsSource
) -> None:
    evil = respx_mock.get("https://evil.example.invalid/x.ttf").respond(200, content=_TTF)
    plain = respx_mock.get("http://fonts.gstatic.com/x.ttf").respond(200, content=_TTF)
    for url in ("https://evil.example.invalid/x.ttf", "http://fonts.gstatic.com/x.ttf"):
        respx_mock.get(_CSS_ROUTE).respond(200, text=_css((400, "normal", url)))
        with pytest.raises(FontUnavailable):
            await source.fetch("Lato", (400,))
    assert not evil.called and not plain.called


async def test_liberation_is_fetched_as_its_metric_twin(
    respx_mock: respx.MockRouter, source: GoogleFontsSource
) -> None:
    css = respx_mock.get(_CSS_ROUTE).respond(
        200, text=_css((400, "normal", "https://fonts.gstatic.com/s/arimo/r.ttf"))
    )
    respx_mock.get("https://fonts.gstatic.com/s/arimo/r.ttf").respond(200, content=_TTF)
    files = await source.fetch("Liberation Sans", (400,))
    assert css.calls.last.request.url.params["family"] == "Arimo:wght@400"
    assert files[0].family == "Liberation Sans" and files[0].asset_name == "liberation-sans-400.ttf"


async def test_family_outside_catalog_is_never_requested(
    respx_mock: respx.MockRouter, source: GoogleFontsSource
) -> None:
    route = respx_mock.get(_CSS_ROUTE).respond(200, text=_LATO)
    for family in ("Arial", "MaPoliceMaison", "Lato;evil"):
        with pytest.raises(FontUnavailable):
            await source.fetch(family)
    with pytest.raises(FontUnavailable):
        await source.fetch("Lato", (450, 1000))
    assert not route.called


@pytest.mark.parametrize(
    "case", ["css_500", "file_404", "redirect", "too_big", "not_a_font", "no_face", "network"]
)
async def test_google_source_unavailable_is_readable(
    respx_mock: respx.MockRouter,
    source: GoogleFontsSource,
    caplog: pytest.LogCaptureFixture,
    case: str,
) -> None:
    caplog.set_level("INFO")
    file_url = "https://fonts.gstatic.com/s/lato/v25/regular.ttf"
    css_text = (
        _css((400, "normal", file_url)) if case != "no_face" else _css((400, "italic", file_url))
    )
    css = respx_mock.get(_CSS_ROUTE)
    font = respx_mock.get(file_url)
    css.respond(500) if case == "css_500" else css.respond(200, text=css_text)
    if case == "network":
        css.side_effect = httpx.ConnectError("refus de https://fonts.googleapis.com")
    responses = {
        "file_404": httpx.Response(404),
        "redirect": httpx.Response(302, headers={"location": "https://evil.example.invalid/"}),
        "too_big": httpx.Response(200, content=b"\x00\x01\x00\x00" * (FONT_MAX_BYTES // 4 + 1)),
        "not_a_font": httpx.Response(200, content=b"<html>pas une police</html>"),
    }
    font.mock(return_value=responses.get(case, httpx.Response(200, content=_TTF)))
    with pytest.raises(FontUnavailable) as caught:
        await source.fetch("Lato", (400,))
    assert caught.value.status_code == 502 and caught.value.code == "font_unavailable"
    assert caught.value.__cause__ is None
    ours = " ".join(r.getMessage() for r in caplog.records if r.name == google.__name__)
    assert "Lato" in ours and "gstatic" not in ours and "googleapis" not in ours


async def test_timeout_is_total_per_request(
    respx_mock: respx.MockRouter, source: GoogleFontsSource, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, text=_LATO)

    monkeypatch.setattr(google, "FONT_TIMEOUT_S", 0.1)
    respx_mock.get(_CSS_ROUTE).mock(side_effect=slow)
    with pytest.raises(FontUnavailable):
        await source.fetch("Lato")
