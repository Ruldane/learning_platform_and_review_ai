"""Google Fonts réel (réseau) : désélectionné par défaut (`-m live`)."""

import pytest

from app.providers.fonts.google import GoogleFontsSource, fonts_http

pytestmark = pytest.mark.live


@pytest.mark.parametrize("family", ["Lato", "Liberation Serif", "Source Sans 3"])
async def test_real_fonts_are_truetype(family: str) -> None:
    async with fonts_http() as http:
        files = await GoogleFontsSource(http).fetch(family)
    assert [(f.weight, f.suffix) for f in files] == [(400, ".ttf"), (700, ".ttf")]
    assert all(f.data[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO") for f in files)
