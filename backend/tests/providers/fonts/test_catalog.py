"""Catalogue des polices libres et choix d'une police de remplacement (D119)."""

import pytest

from app.providers.fonts.base import FontFile, FontUnavailable
from app.providers.fonts.catalog import FREE_FAMILIES, SUBSTITUTES, choose_font, clean_name
from app.providers.fonts.fake import FakeFontSource


@pytest.mark.parametrize(
    ("pdf_font", "family", "free"),
    [
        ("ABCDEF+Lato-Bold", "Lato", True),
        ("ArialMT", "Liberation Sans", False),
        ("Calibri", "Carlito", False),
        ("TimesNewRomanPS", "Liberation Serif", False),
        ("MaPoliceMaison", "Liberation Sans", False),
        ("TimesNewRomanPS-BoldMT", "Liberation Serif", False),
        ("Arial,Bold", "Liberation Sans", False),
        ("Helvetica-Bold", "Liberation Sans", False),
        ("XYZABC+SourceSans3-Regular", "Source Sans 3", True),
        ("SourceSansPro-Semibold", "Source Sans 3", False),
        ("OpenSans-Italic", "Open Sans", True),
        ("RobotoSlab-Bold", "Roboto Slab", True),
        ("LiberationSerif", "Liberation Serif", True),
        ("Cambria-Bold", "Caladea", False),
        ("Georgia", "Gelasio", False),
        ("SegoeUI-Semibold", "Noto Sans", False),
        ("MaPoliceSerif", "Liberation Serif", False),
        ("MaPoliceSansSerif", "Liberation Sans", False),
        ("F1", "Liberation Sans", False),
        ("", "Liberation Sans", False),
    ],
)
def test_choose_font(pdf_font: str, family: str, free: bool) -> None:
    choice = choose_font(pdf_font)
    assert (choice.family, choice.free) == (family, free)
    assert choice.family in FREE_FAMILIES


def test_original_is_the_cleaned_name() -> None:
    assert clean_name("ABCDEF+TimesNewRomanPSMT") == "TimesNewRoman"
    assert choose_font("ABCDEF+ArialMT").original == "Arial"


def test_catalog_and_substitutes() -> None:
    assert len(FREE_FAMILIES) == 26 and {"Carlito", "Caladea", "Gelasio"} <= FREE_FAMILIES
    assert set(SUBSTITUTES.values()) <= FREE_FAMILIES
    assert SUBSTITUTES["arial"] == SUBSTITUTES["helvetica"] == "Liberation Sans"
    assert SUBSTITUTES["calibri"] == "Carlito" and SUBSTITUTES["cambria"] == "Caladea"


def test_asset_name_is_a_resource_slug() -> None:
    assert (
        FontFile("Source Sans 3", 400, "normal", b"", ".ttf").asset_name == "source-sans-3-400.ttf"
    )
    assert FontFile("Lato", 700, "italic", b"", ".woff2").asset_name == "lato-700-italic.woff2"


async def test_fake_source_gives_one_small_ttf_per_weight() -> None:
    source = FakeFontSource(unavailable={"Lora"})
    files = await source.fetch("Lato")
    assert [(f.family, f.weight, f.suffix) for f in files] == [
        ("Lato", 400, ".ttf"),
        ("Lato", 700, ".ttf"),
    ]
    assert all(f.data.startswith(b"\x00\x01\x00\x00") for f in files)
    for family in ("Lora", "Arial"):
        with pytest.raises(FontUnavailable):
            await source.fetch(family)
    assert source.calls[0] == ("Lato", (400, 700))
