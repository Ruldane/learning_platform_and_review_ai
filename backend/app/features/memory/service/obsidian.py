"""En-tête et renvois wiki d'une note Markdown synchronisée."""

import re
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.features.memory.service.rules import clean_tags
from app.features.memory.service.text import clean_display

_HEADER_LIMIT = 16 * 1024
_HEADER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
_WIKI = re.compile(r"\[\[([^\]|#\r\n]{1,200})(?:[|#][^\]\r\n]{0,200})?\]\]")


def split_header(text: str) -> tuple[str, str]:
    header = _HEADER.match(text[:_HEADER_LIMIT])
    return (header.group(1), text[header.end() :]) if header is not None else ("", text)


def _tags(raw: object) -> list[str]:
    values = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return clean_tags([value.lstrip("#") for value in values if isinstance(value, str)])


def note_metadata(text: str) -> dict[str, Any]:
    header, body = split_header(text)
    try:
        data = yaml.safe_load(header) if header else None
    except (yaml.YAMLError, RecursionError, ValueError):
        data = None
    data = data if isinstance(data, dict) else {}
    title = clean_display(data.get("title")) if isinstance(data.get("title"), str) else ""
    links: dict[str, None] = {}
    for match in _WIKI.finditer(body):
        if note := clean_display(match.group(1)):
            links.setdefault(note, None)
        if len(links) == 100:
            break
    return {"title": title, "tags": _tags(data.get("tags")), "links": list(links)}
