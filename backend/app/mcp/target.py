"""The label of the target of a « À confirmer » request (phase 10, P15): January reads « Company —
Title » rather than an identifier. Read by the GET route of the same resource when it is declared
(the route's own; otherwise that of its parent resource: `POST /applications/{id}/events` reads
`GET /applications/{id}`)."""

from typing import Any

from app.mcp.arguments import clip
from app.mcp.envelope import fence, scrub_text
from app.mcp.registry import Registry
from app.mcp.tools import ToolSpec

_KEYS = ("company", "title", "name", "label", "subject")  # something to name a target with
_PARTS = 2
_PART_MAX = 80


def reader_of_target(registry: Registry, tool: ToolSpec, path: str) -> tuple[ToolSpec, str] | None:
    """The read tool for `tool`'s target and the path to read (`path`: the request's), or `None`: a
    route without an identifier, or no read declared."""
    if tool.route is None:
        return None
    template, concrete = tool.route[1].split("/"), path.split("/")
    if len(concrete) != len(template):
        return None
    for size in (len(template), len(template) - 1):
        wanted = "/".join(template[:size])
        reader = registry.reader_of(wanted)
        if reader is not None and "{" in wanted:
            return reader, "/".join(concrete[:size])
    return None


def label_of(data: Any, reader: ToolSpec) -> str | None:
    """The name of a read resource: its `company`, `title`, `name`... fields (two at most), keys
    masked
    **then** cut (never a key cut in two), before wrapping those the read declares untrusted."""
    if not isinstance(data, dict):
        return None
    parts = {
        key: clip(scrub_text(str(data[key])), _PART_MAX)
        for key in _KEYS
        if isinstance(data.get(key), str) and data[key].strip()
    }
    kept = dict(list(parts.items())[:_PARTS])
    label = " — ".join(str(value) for value in fence(kept, reader.untrusted).values())
    return label or None
