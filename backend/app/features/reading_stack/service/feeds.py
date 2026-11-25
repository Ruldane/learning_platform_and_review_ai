"""Read an RSS or Atom feed provided by the web reader."""

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from app.core.errors import AppError
from app.features.memory.service.upload import normalize_url

MAX_FEED_BYTES = 1024 * 1024
MAX_FEED_ENTRIES = 30
_ATOM = "{http://www.w3.org/2005/Atom}"
_TAGS = re.compile(r"<[^>]*>")


@dataclass(frozen=True)
class FeedEntry:
    url: str
    title: str
    summary: str


def _text(node: Element, name: str, limit: int) -> str:
    part = node.find(name)
    if part is None:
        return ""
    value = unescape(" ".join(part.itertext()))
    return " ".join(_TAGS.sub(" ", value).split())[:limit]


def _atom_link(node: Element) -> str:
    for link in node.iterfind(f"{_ATOM}link"):
        if link.get("rel", "alternate") == "alternate" and (href := link.get("href")):
            return href.strip()
    return ""


def _entry(node: Element, base_url: str, atom: bool) -> FeedEntry | None:
    prefix = _ATOM if atom else ""
    link = _atom_link(node) if atom else (node.findtext("link") or "").strip()
    if not link:
        return None
    try:
        url = normalize_url(urljoin(base_url, link))
    except (ValueError, AppError):
        return None
    title = _text(node, f"{prefix}title", 240)
    if not title:
        return None
    description = f"{_ATOM}summary" if atom else "description"
    return FeedEntry(url, title, _text(node, description, 600))


def parse_feed(body: bytes, final_url: str) -> list[FeedEntry]:
    if len(body) > MAX_FEED_BYTES:
        return []
    try:
        root = fromstring(body, forbid_dtd=True)
    except (ParseError, DefusedXmlException, LookupError):
        return []
    atom = root.tag == f"{_ATOM}feed"
    path = f"{_ATOM}entry" if atom else "channel/item"
    found: dict[str, FeedEntry] = {}
    for node in root.iterfind(path):
        item = _entry(node, final_url, atom)
        if item is not None:
            found.setdefault(item.url, item)
        if len(found) == MAX_FEED_ENTRIES:
            break
    return list(found.values())
