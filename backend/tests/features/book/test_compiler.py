import re
from base64 import b64decode
from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from xml.etree.ElementTree import fromstring
from zipfile import ZIP_STORED, ZipFile

import pytest

from app.features.book.service.compiler import compile_book
from app.features.book.service.models import BookChapter, BookNote, BookSource, GlossaryEntry
from app.providers.pdf.base import PageLayout, PdfLayout, RenderFailed
from tests.support.memory import FakeHtmlRenderer

XHTML = {"x": "http://www.w3.org/1999/xhtml"}
OPF = {"p": "http://www.idpf.org/2007/opf"}
CONTAINER = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}


@pytest.fixture
def source() -> BookSource:
    return BookSource(
        program_id="program-42",
        title="Python & données",
        modified_at=datetime(2026, 11, 22, 8, 0, tzinfo=UTC),
        chapters=(
            BookChapter(
                rank=4,
                title="Itérations avancées",
                markdown="## Explication\n\nRéutilise la boucle.\n\nEntrée&nbsp;sortie.\n",
                terms=("BOUCLE", "Générateur"),
            ),
            BookChapter(
                rank=1,
                title="Première boucle",
                markdown=(
                    "# Première boucle\n\n## Explication\n\nLa première notion.\n\n"
                    "## Erreurs fréquentes\n\nÉviter la boucle infinie.\n\n"
                    "## Exercice\n\nÉcrire une boucle.\n\n"
                    "~~~python\nfor i in range(3):\n    print(i)\n~~~\n\n"
                    "## Corrigé de l’exercice\n\nComparer la sortie.\n\n"
                    "## Sources\n\n1. Documentation\n"
                ),
                notes=(
                    BookNote(
                        title="Astuce <locale>",
                        markdown=(
                            "Ma note liée.\n\n<script>alerte()</script>\n\n"
                            "![Image distante](https://example.test/image.png)\n"
                        ),
                    ),
                ),
                terms=("Boucle",),
            ),
        ),
        glossary=(
            GlossaryEntry("Générateur", "Produit des valeurs à la demande."),
            GlossaryEntry("Boucle", "Répète un bloc."),
        ),
    )


async def test_pdf_uses_published_chapter_order_and_shared_sections(source: BookSource) -> None:
    renderer = FakeHtmlRenderer()
    compiled = await compile_book(source, renderer)

    assert compiled.pdf.startswith(b"%PDF")
    (document,) = renderer.documents
    html = document.index_html
    assert html.index('id="cover"') < html.index('id="contents"')
    assert html.index('id="chapter-1"') < html.index('id="chapter-4"')
    assert html.index('id="chapter-4"') < html.index('id="exercises"')
    assert "Python &amp; données" in html
    assert "Erreurs fréquentes" in html and 'class="lesson-section callout callout-warning"' in html
    assert "Astuce &lt;locale&gt;" in html and "Ma note liée." in html
    assert "for i in range(3):" in html.split('id="exercises"', 1)[1]
    assert "Comparer la sortie." in html.split('id="exercises"', 1)[1]
    assert "for i in range(3):" not in html.split('id="exercises"', 1)[0]
    assert "Répète un bloc." in html and "Produit des valeurs à la demande." in html
    assert "<script" not in html and "<img" not in html and "https://example.test" not in html
    assert document.footer_html is not None and "pageNumber" in document.footer_html
    assert set(document.assets) == {"book.css"}
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert set(re.findall(r'\bhref="#([^"]+)"', html)).issubset(ids)


async def test_epub_reproducible_navigation_and_spine(source: BookSource) -> None:
    first = await compile_book(source, FakeHtmlRenderer())
    second = await compile_book(source, FakeHtmlRenderer())
    assert first.epub == second.epub

    with ZipFile(BytesIO(first.epub)) as epub:
        head = epub.infolist()[0]
        assert (head.filename, head.compress_type, head.extra) == ("mimetype", ZIP_STORED, b"")
        assert epub.read(head) == b"application/epub+zip"
        container = fromstring(epub.read("META-INF/container.xml"))
        (rootfile,) = container.findall(".//c:rootfile", CONTAINER)
        package = fromstring(epub.read(rootfile.attrib["full-path"]))
        assert package.attrib["version"] == "3.0"
        expected = ["cover", "contents", "chapter-1", "chapter-4", "exercises", "glossary", "index"]
        assert [item.attrib["idref"] for item in package.findall(".//p:itemref", OPF)] == expected
        items = {item.attrib["id"]: item.attrib for item in package.findall(".//p:item", OPF)}
        assert items["contents"]["properties"] == "nav"
        pages = {item: fromstring(epub.read(f"EPUB/{items[item]['href']}")) for item in expected}
        assert [link.get("href") for link in pages["contents"].findall(".//x:nav//x:a", XHTML)] == [
            f"{items[item]['href']}#{item}" for item in expected if item != "contents"
        ]
        assert {link.get("href") for link in pages["index"].findall(".//x:a", XHTML)} >= {
            "chapter-1.xhtml#chapter-1",
            "chapter-4.xhtml#chapter-4",
        }
        assert len(pages["chapter-1"].findall(".//x:script", XHTML)) == 0
        assert "Entrée\xa0sortie." in "".join(pages["chapter-4"].itertext())
        assert "print(i)" in "".join(pages["exercises"].itertext())


async def test_pdf_failure_propagates_without_a_partial_book(source: BookSource) -> None:
    renderer = FakeHtmlRenderer()
    renderer.failures = 1
    with pytest.raises(RenderFailed) as error:
        await compile_book(source, renderer)
    assert source.title not in str(error.value)


async def test_mermaid_is_rendered_as_an_accessible_image_in_both_formats(
    source: BookSource,
) -> None:
    png = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/efEphkAAAAASUVORK5CYII="
    )

    class FakeLayout:
        async def extract_layout(self, data: bytes, *, max_pages: int = 4) -> PdfLayout:
            assert data.startswith(b"%PDF") and max_pages >= 1
            return PdfLayout([PageLayout(842, 595, [], png, "Entrée Sortie")], [], True)

    chapter = replace(
        source.chapters[0],
        markdown="## Schémas\n\n```mermaid\nflowchart LR\n  A[Entrée] --> B[Sortie]\n```\n",
    )
    book = replace(source, chapters=(chapter,))
    renderer = FakeHtmlRenderer()
    files = await compile_book(book, renderer, diagram_layout=FakeLayout())

    diagram_document, book_document = renderer.documents
    assert diagram_document.wait_for_expression == "window.__lessonReady === true"
    assert set(diagram_document.assets) >= {"mermaid.min.js", "render.js"}
    assert 'class="mermaid"' in diagram_document.index_html
    assert 'src="data:image/png;base64,' in book_document.index_html
    assert 'alt="Entrée → Sortie"' in book_document.index_html
    assert "<figcaption>Entrée → Sortie</figcaption>" in book_document.index_html
    assert "flowchart" not in book_document.index_html and "<script" not in book_document.index_html

    with ZipFile(BytesIO(files.epub)) as epub:
        page = fromstring(epub.read("EPUB/chapter-4.xhtml"))
        (figure,) = page.findall(".//x:figure/x:img", XHTML)
        assert figure.attrib["alt"] == "Entrée → Sortie"
        package = fromstring(epub.read("EPUB/package.opf"))
        (entry,) = package.findall('.//p:item[@media-type="image/png"]', OPF)
        assert entry.attrib["href"] == figure.attrib["src"]
        assert epub.read(f"EPUB/{entry.attrib['href']}") == png
        assert len(page.findall(".//x:script", XHTML)) == 0
