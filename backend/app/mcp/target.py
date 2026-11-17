"""Le libellé de la cible d'une demande « À confirmer » (phase 10, P15) : January lit « Société —
Titre » plutôt qu'un identifiant. Lu par la route GET de la même ressource quand elle est déclarée
(celle de la route ; sinon celle de sa ressource mère : `POST /applications/{id}/events` lit
`GET /applications/{id}`)."""

from typing import Any

from app.mcp.arguments import clip
from app.mcp.envelope import fence, scrub_text
from app.mcp.registry import Registry
from app.mcp.tools import ToolSpec

_KEYS = ("company", "title", "name", "label", "subject")  # de quoi nommer une cible
_PARTS = 2
_PART_MAX = 80


def reader_of_target(registry: Registry, tool: ToolSpec, path: str) -> tuple[ToolSpec, str] | None:
    """L'outil de lecture de la cible de `tool` et le chemin à lire (`path` : celui de la requête),
    ou `None` : route sans identifiant, ou aucune lecture déclarée."""
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
    """Le nom d'une ressource lue : ses champs `company`, `title`, `name`… (deux au plus), les clés
    masquées **puis** la coupe (jamais une clé coupée en deux), avant d'entourer ceux que la lecture
    déclare non fiables."""
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
