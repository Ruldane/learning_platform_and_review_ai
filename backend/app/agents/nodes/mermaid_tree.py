"""The parsed Mermaid tree shared by the grammar and emitter (D85 §11f).

Labels hold decoded text. The grammar resolves Mermaid entities and converts line breaks
to newline characters. The emitter escapes labels with its own entities.
"""

import html
import re
from dataclasses import dataclass, field

# Longest delimiter pairs first. The index identifies the shape in the parsed tree.
SHAPES = (
    ("([", "])"),
    ("[[", "]]"),
    ("[(", ")]"),
    ("((", "))"),
    ("{{", "}}"),
    ("[", "]"),
    ("(", ")"),
    ("{", "}"),
    (">", "]"),
)
RECTANGLE = SHAPES.index(("[", "]"))

# Possessive quantifiers keep entity parsing linear (D85 §11f, round 4).
_ENTITY = re.compile(r"#(\d++|[A-Za-z][A-Za-z0-9]*+);")
_BREAK = re.compile(r"<br[ \t]*+/?>", re.IGNORECASE)


class MermaidSyntaxError(ValueError):
    """A grammar error with a diagnostic for the Scribe."""


@dataclass(frozen=True)
class NodeRef:
    key: str
    shape: int | None = None
    label: str | None = None


@dataclass(frozen=True)
class Edge:
    arrow: str
    label: str | None = None


@dataclass(frozen=True)
class Chain:
    groups: list[list[NodeRef]]
    edges: list[Edge]


@dataclass(frozen=True)
class Subgraph:
    key: str
    label: str | None = None


@dataclass(frozen=True)
class End:
    pass


@dataclass(frozen=True)
class Direction:
    value: str


Statement = Chain | Subgraph | End | Direction


@dataclass
class Flowchart:
    direction: str
    statements: list[Statement] = field(default_factory=list)


def _decode(match: re.Match[str]) -> str:
    name = match.group(1)
    source = f"&#{name};" if name.isdigit() else f"&{name};"
    text = html.unescape(source)
    return match.group(0) if text == source else text


def label_text(raw: str) -> str:
    """Decode entities and line breaks and collapse whitespace within each line."""
    parts = _BREAK.split(_ENTITY.sub(_decode, raw))
    return "\n".join(" ".join(part.split()) for part in parts).strip("\n")
