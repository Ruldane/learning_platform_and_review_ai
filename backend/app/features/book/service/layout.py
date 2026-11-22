"""Structure du livre en HTML pour l'impression et en XHTML pour la liseuse."""

from dataclasses import dataclass
from xml.etree.ElementTree import Element, SubElement

from app.features.book.service.content import PreparedBook, PreparedChapter, xml_text

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
STYLESHEET = "book.css"
BOOK_CSS = b"""
html { color: #17222b; background: #fff; line-height: 1.45; }
body { margin: 1em auto; max-width: 55em; padding: 0 0.5em; }
h1, h2, h3, h4, h5 { line-height: 1.2; break-after: avoid; }
a { color: #184780; }
pre { background: #f1f4f7; padding: 0.6em; white-space: pre-wrap; overflow-wrap: anywhere; }
table { border-collapse: collapse; max-width: 100%; }
td, th { border: 1px solid #7d8b96; padding: 0.3em; }
dd { margin-block-end: 0.75em; }
.cover { padding-block-start: 20%; }
.callout-warning {
  border-inline-start: 0.25em solid #956000; background: #fff6d9; padding: 0.25em 0.75em;
}
.chapter-notes {
  border-inline-start: 0.25em solid #54718a; background: #f1f4f7; padding: 0.25em 0.75em;
}
@media screen and (min-width: 46em), print {
  .chapter-notes { float: right; width: 30%; margin: 0 0 1em 1em; }
  .book-page { display: flow-root; }
}
@media print {
  body { margin: 0; padding: 0; max-width: none; }
  .book-page + .book-page { break-before: page; }
}
"""

_CSP = "default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'"


@dataclass(frozen=True)
class BookPage:
    id: str
    title: str
    element: Element


@dataclass(frozen=True)
class _Links:
    epub: bool

    def href(self, page: str, anchor: str | None = None) -> str:
        file = f"{page}.xhtml" if self.epub else ""
        return f"{file}#{anchor or page}"


def _text(parent: Element, tag: str, text: str) -> Element:
    element = SubElement(parent, tag)
    element.text = xml_text(text)
    return element


def _link(parent: Element, label: str, href: str) -> None:
    _text(parent, "a", label).set("href", href)


def _section(id: str, title: str) -> BookPage:
    element = Element("section", {"id": id, "class": "book-page"})
    _text(element, "h2", title)
    return BookPage(id, title, element)


def _cover(book: PreparedBook, epub: bool) -> BookPage:
    element = Element("section", {"id": "cover", "class": "book-page cover"})
    if epub:
        element.set("epub:type", "cover")
    _text(element, "h1", book.source.title)
    if not book.chapters:
        _text(element, "p", "Aucun chapitre publié.")
    return BookPage("cover", "Couverture", element)


def _contents(pages: list[BookPage], links: _Links) -> BookPage:
    page = _section("contents", "Sommaire")
    nav = SubElement(page.element, "nav", {"aria-label": page.title})
    if links.epub:
        nav.set("epub:type", "toc")
    entries = SubElement(nav, "ol")
    for item in pages:
        _link(SubElement(entries, "li"), item.title, links.href(item.id))
    return page


def _chapter(chapter: PreparedChapter, links: _Links) -> BookPage:
    page = _section(chapter.anchor, chapter.label)
    if chapter.notes:
        aside = SubElement(page.element, "aside", {"class": "chapter-notes"})
        _text(aside, "h3", "Notes Obsidian")
        for note in chapter.notes:
            _text(aside, "h4", note.title)
            aside.extend(note.body)
    page.element.extend(chapter.body)
    if chapter.exercises:
        _link(
            SubElement(page.element, "p"),
            "Voir les exercices et corrigés de ce chapitre",
            links.href("exercises", f"exercises-{chapter.anchor}"),
        )
    return page


def _exercises(book: PreparedBook, links: _Links) -> BookPage:
    page = _section("exercises", "Annexe · Exercices et corrigés")
    chapters = [chapter for chapter in book.chapters if chapter.exercises]
    if not chapters:
        _text(page.element, "p", "Aucun exercice publié.")
    for chapter in chapters:
        section = SubElement(page.element, "section", {"id": f"exercises-{chapter.anchor}"})
        _text(section, "h3", chapter.label)
        section.extend(chapter.exercises)
        _link(SubElement(section, "p"), "Revenir au chapitre", links.href(chapter.anchor))
    return page


def _glossary(book: PreparedBook) -> BookPage:
    page = _section("glossary", "Glossaire")
    if book.glossary:
        entries = SubElement(page.element, "dl")
        for item in book.glossary:
            _text(entries, "dt", item.term)
            _text(entries, "dd", item.definition)
    else:
        _text(page.element, "p", "Aucune notion dans le glossaire.")
    return page


def _index(book: PreparedBook, links: _Links) -> BookPage:
    page = _section("index", "Index")
    if not book.index:
        _text(page.element, "p", "Aucune entrée dans l’index.")
        return page
    entries = SubElement(page.element, "dl")
    for item in book.index:
        _text(entries, "dt", item.term)
        chapters = SubElement(SubElement(entries, "dd"), "ul")
        for chapter in item.chapters:
            _link(SubElement(chapters, "li"), chapter.label, links.href(chapter.anchor))
    return page


def book_pages(book: PreparedBook, *, epub: bool) -> list[BookPage]:
    links = _Links(epub)
    cover = _cover(book, epub)
    pages = [
        *(_chapter(chapter, links) for chapter in book.chapters),
        _exercises(book, links),
        _glossary(book),
        _index(book, links),
    ]
    return [cover, _contents([cover, *pages], links), *pages]


def book_document(title: str, language: str, pages: list[BookPage], *, epub: bool) -> Element:
    root = Element("html", {"lang": xml_text(language)})
    if epub:
        root.attrib.update(
            {"xmlns": XHTML_NS, "xmlns:epub": EPUB_NS, "xml:lang": xml_text(language)}
        )
    head = SubElement(root, "head")
    SubElement(head, "meta", {"charset": "utf-8"})
    _text(head, "title", title)
    if not epub:
        SubElement(head, "meta", {"http-equiv": "Content-Security-Policy", "content": _CSP})
    SubElement(head, "link", {"rel": "stylesheet", "href": STYLESHEET})
    body = SubElement(root, "body")
    body.extend(page.element for page in pages)
    return root
