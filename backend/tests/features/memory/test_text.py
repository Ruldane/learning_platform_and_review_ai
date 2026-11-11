import pytest

from app.features.memory.service.text import (
    CHUNK_OVERLAP,
    CHUNK_TOKENS,
    chunk_text,
    clean_display,
    clean_text,
    content_hash,
    count_tokens,
    display_name,
    source_hash,
)


def test_chunk_text_windows_and_overlap() -> None:
    chunks = chunk_text(" ".join(f"m{i}" for i in range(1000)))
    assert [c.token_count for c in chunks] == [500, 500, 120]
    assert chunks[1].text.split()[0] == "m440" and chunks[2].text.split()[0] == "m880"
    assert [c.ordinal for c in chunks] == [0, 1, 2]


def test_chunk_text_short_and_empty() -> None:
    assert chunk_text("") == [] and chunk_text(" \n ") == []
    assert len(chunk_text("un deux")) == 1
    assert [c.token_count for c in chunk_text(" ".join("x" * 501))] == [500, 61]


def test_chunk_text_constants_and_exact_size() -> None:
    assert (CHUNK_TOKENS, CHUNK_OVERLAP) == (500, 60)
    assert len(chunk_text(" ".join("x" * 500))) == 1  # la fenêtre atteint la fin : on s'arrête


def test_chunk_text_is_a_slice_of_the_original() -> None:
    text = "Début,   avec\nretours.\n\nFin !"
    (chunk,) = chunk_text(text)
    assert chunk.text == text
    padded = chunk_text("  " + text + "  \n")
    assert padded[0].text == text  # du début du 1er token à la fin du dernier


def test_chunk_text_small_windows() -> None:
    chunks = chunk_text("a b c d e f", size=3, overlap=1)
    assert [c.text for c in chunks] == ["a b c", "c d e", "e f"]
    assert [c.token_count for c in chunks] == [3, 3, 2]


def test_chunk_text_rejects_bad_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_text("a b", size=3, overlap=3)
    with pytest.raises(ValueError):
        chunk_text("a b", size=0, overlap=0)


def test_count_tokens_splits_words_and_punctuation() -> None:
    assert count_tokens("Bonjour, le monde !") == 5
    assert count_tokens("") == 0


def test_clean_text_normalizes() -> None:
    assert clean_text("a\u00a0b\r\n\r\n\r\n\r\nc\x00") == "a b\n\nc"


def test_clean_text_details() -> None:
    assert clean_text("e\u0301") == "\u00e9"  # NFC
    assert clean_text("ligne   \nsuite\t\n\tretrait") == "ligne\nsuite\n\tretrait"
    assert clean_text("a\rb") == "a\nb"
    assert clean_text("a\x0bb\x07") == "ab"
    assert clean_text("\n\n  texte  \n\n") == "texte"


def test_content_hash_rules() -> None:
    assert content_hash("acquis", "Python ", "x") == content_hash("acquis", "python", "y")
    assert content_hash("document", "t", "Bonjour  le monde") == content_hash(
        "document", "autre", "bonjour le monde"
    )
    assert content_hash("lecon", "t", "a") != content_hash("source", "t", "a")
    assert len(content_hash("lecon", "t", "a")) == 64


def test_source_hash_is_sha256_hex() -> None:
    assert source_hash(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\x\\cv.pdf", "cv.pdf"),
        ("\x00\n", "Document sans nom"),
        (None, "Document sans nom"),
        ("", "Document sans nom"),
        ("dossier/", "dossier"),
        ("  Mon CV\x07.pdf ", "Mon CV.pdf"),
    ],
)
def test_display_name(raw: str | None, expected: str) -> None:
    assert display_name(raw) == expected


def test_display_name_is_capped_and_normalized() -> None:
    assert len(display_name("a" * 500)) == 200
    assert display_name("e\u0301.txt") == "\u00e9.txt"


# Construits par `chr` : un caractère invisible ne doit pas l'être aussi dans le source du test.
RLO, LRI, RLI, FSI, PDI = (chr(c) for c in (0x202E, 0x2066, 0x2067, 0x2068, 0x2069))
ZWSP, ESC, LS, PS = chr(0x200B), chr(0x1B), chr(0x2028), chr(0x2029)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (f"facture{RLO}fdp.exe", "facturefdp.exe"),  # forçage droite-à-gauche
        (f"{LRI}cv{PDI}{RLI}.pdf{FSI}", "cv.pdf"),  # isolats bidirectionnels
        (f"c{ZWSP}v.pdf", "cv.pdf"),  # espace de largeur nulle
        (f"cv{ESC}[31m.pdf", "cv[31m.pdf"),  # ESC
        (f"ligne{LS}suite{PS}.pdf", "lignesuite.pdf"),  # séparateurs de ligne, de paragraphe
        ("  trop   d'espaces" + chr(9) + ".pdf ", "trop d'espaces.pdf"),  # tabulation : Cc
    ],
)
def test_display_name_drops_invisible_characters(raw: str, expected: str) -> None:
    assert display_name(raw) == expected
    assert clean_display(raw) == expected


def test_clean_display_is_capped_and_may_be_empty() -> None:
    assert len(clean_display("é" * 500)) == 200
    assert clean_display(f"{RLO}{ZWSP} " + chr(10)) == "" and clean_display(None) == ""
