"""Emballage EPUB 3 de l'édition, sans date ni chemin dépendant de la machine."""

from datetime import UTC
from io import BytesIO
from urllib.parse import quote
from xml.etree.ElementTree import Element, ElementTree, SubElement
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from app.features.book.service.content import PreparedBook, xml_text
from app.features.book.service.layout import (
    BOOK_CSS,
    STYLESHEET,
    BookPage,
    book_document,
    book_pages,
)
from app.features.book.service.models import BookSource

_MIMETYPE = b"application/epub+zip"
_PACKAGE = "EPUB/package.opf"
_XHTML_MIME = "application/xhtml+xml"
_OPF_NS = "http://www.idpf.org/2007/opf"
_DC_NS = "http://purl.org/dc/elements/1.1/"
_CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
_CONTENTS_ID = "contents"


def _xml(document: Element) -> bytes:
    buffer = BytesIO()
    ElementTree(document).write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def _container() -> bytes:
    container = Element("container", {"version": "1.0", "xmlns": _CONTAINER_NS})
    rootfiles = SubElement(container, "rootfiles")
    SubElement(
        rootfiles,
        "rootfile",
        {"full-path": _PACKAGE, "media-type": "application/oebps-package+xml"},
    )
    return _xml(container)


def _metadata(package: Element, source: BookSource) -> None:
    metadata = SubElement(package, "metadata", {"xmlns:dc": _DC_NS})
    publisher_id = f"urn:tremplin:program:{quote(source.program_id, safe='')}"
    SubElement(metadata, "dc:identifier", {"id": "publication-id"}).text = publisher_id
    SubElement(metadata, "dc:title").text = xml_text(source.title)
    SubElement(metadata, "dc:language").text = xml_text(source.language)
    modified = source.modified_at.astimezone(UTC).isoformat(timespec="seconds")
    SubElement(metadata, "meta", {"property": "dcterms:modified"}).text = modified.replace(
        "+00:00", "Z"
    )


def _package(source: BookSource, pages: list[BookPage]) -> bytes:
    package = Element(
        "package", {"xmlns": _OPF_NS, "version": "3.0", "unique-identifier": "publication-id"}
    )
    _metadata(package, source)
    manifest = SubElement(package, "manifest")
    SubElement(manifest, "item", {"id": "css", "href": STYLESHEET, "media-type": "text/css"})
    spine = SubElement(package, "spine")
    for page in pages:
        item = SubElement(
            manifest, "item", {"id": page.id, "href": f"{page.id}.xhtml", "media-type": _XHTML_MIME}
        )
        if page.id == _CONTENTS_ID:
            item.set("properties", "nav")
        SubElement(spine, "itemref", {"idref": page.id})
    return _xml(package)


def _write(archive: ZipFile, name: str, body: bytes, *, compression: int = ZIP_DEFLATED) -> None:
    entry = ZipInfo(name)
    entry.create_system = 3  # Même en-tête quel que soit l'OS qui prépare l'édition.
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, body, compress_type=compression)


def epub_bytes(book: PreparedBook) -> bytes:
    pages = book_pages(book, epub=True)
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        _write(archive, "mimetype", _MIMETYPE, compression=ZIP_STORED)
        _write(archive, "META-INF/container.xml", _container())
        _write(archive, _PACKAGE, _package(book.source, pages))
        _write(archive, f"EPUB/{STYLESHEET}", BOOK_CSS)
        for page in pages:
            document = book_document(page.title, book.source.language, [page], epub=True)
            _write(archive, f"EPUB/{page.id}.xhtml", _xml(document))
    return buffer.getvalue()
