"""Arbre du Mermaid du Scribe (D85 §11f) : ce que `mermaid_grammar` produit et ce que
`mermaid_rules` réémet. Les libellés y sont du texte décodé (entités Mermaid résolues, `<br>`
devenu `\\n`) : l'échappement est refait à la réémission, par nos propres entités."""

import html
import re
from dataclasses import dataclass, field

# (ouvrant, fermant), les plus longs d'abord ; l'index sert de forme dans l'arbre.
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

# Quantificateurs possessifs : aucun retour arrière, temps linéaire (D85 §11f, round 4).
_ENTITY = re.compile(r"#(\d++|[A-Za-z][A-Za-z0-9]*+);")
_BREAK = re.compile(r"<br[ \t]*+/?>", re.IGNORECASE)


class MermaidSyntaxError(ValueError):
    """Une instruction hors grammaire ; le message est le motif rendu au Scribe."""


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
    """Texte d'un libellé : entités décodées, `<br>` changé en `\\n`, blancs réduits."""
    parts = _BREAK.split(_ENTITY.sub(_decode, raw))
    return "\n".join(" ".join(part.split()) for part in parts).strip("\n")
