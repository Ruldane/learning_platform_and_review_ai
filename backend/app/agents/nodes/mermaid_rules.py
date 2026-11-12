"""Mermaid du Scribe (SPEC 3.3, 17.4, D85 §11f) : le code vient d'un modèle qui a lu des pages
web, il est donc traité comme non fiable. Il n'est pas filtré mais **analysé** par une grammaire
stricte (`mermaid_grammar`), puis **réémis** depuis l'arbre :

- les identifiants deviennent `n1`, `n2`… (ordre de première apparition) ;
- chaque nœud porte, à sa première apparition, sa forme et son libellé, toujours entre guillemets ;
- le texte des libellés est échappé par nos entités : `#`, `&`, `"`, `<`, `>`, `` ` ``, `%` et `|` ;
  `<br>` est le seul HTML produit ;
- une instruction par ligne, `subgraph` indentés.

Seule la version normalisée sort : `board.update`, le port, puis le PDF (4.8). Taille bornée :
lignes, nœuds, longueur des libellés ; caractères de contrôle ou de format invisibles refusés."""

import unicodedata

from app.agents.nodes.mermaid_grammar import parse_flowchart
from app.agents.nodes.mermaid_tree import (
    RECTANGLE,
    SHAPES,
    Chain,
    Direction,
    End,
    Flowchart,
    NodeRef,
    Subgraph,
)

MAX_MERMAID_LINES = 80
MAX_NODES = 40
MAX_LABEL_CHARS = 80

_ALLOWED_CONTROLS = {"\t", "\n", "\r"}
_ESCAPES = str.maketrans(
    {
        "#": "#35;",
        "&": "#amp;",
        '"': "#quot;",
        "<": "#lt;",
        ">": "#gt;",
        "`": "#96;",
        "%": "#37;",
        "|": "#124;",
        # Sans `:`, ni les icônes `fa:` ni la règle `style…:…#…;` de Mermaid (qui retire le `;`
        # d'une entité) ne s'appliquent au texte.
        ":": "#58;",
    }
)


def _invisible(char: str) -> bool:
    """Caractère de contrôle (hors tabulation et fins de ligne) ou de format (U+200B…)."""
    return char not in _ALLOWED_CONTROLS and unicodedata.category(char) in ("Cc", "Cf")


def _refs(chart: Flowchart) -> list[NodeRef]:
    return [
        ref
        for statement in chart.statements
        if isinstance(statement, Chain)
        for group in statement.groups
        for ref in group
    ]


def _labels(chart: Flowchart) -> list[str]:
    labels = [ref.label for ref in _refs(chart) if ref.label is not None]
    for statement in chart.statements:
        if isinstance(statement, Chain):
            labels += [edge.label for edge in statement.edges if edge.label is not None]
        elif isinstance(statement, Subgraph) and statement.label is not None:
            labels.append(statement.label)
    return labels


def _chart_problems(chart: Flowchart) -> list[str]:
    problems: list[str] = []
    labels = _labels(chart)
    if any(_invisible(char) for label in labels for char in label):
        problems.append("caractère invisible ou de contrôle dans un libellé")
    if len(chart.statements) + 1 > MAX_MERMAID_LINES:
        problems.append(f"plus de {MAX_MERMAID_LINES} lignes")
    subgraphs = {s.key for s in chart.statements if isinstance(s, Subgraph)}
    nodes = {ref.key for ref in _refs(chart)} - subgraphs
    if not nodes:
        problems.append("aucun nœud")
    if len(nodes) > MAX_NODES:
        problems.append(f"plus de {MAX_NODES} nœuds")
    if any(len(label) > MAX_LABEL_CHARS for label in labels):
        problems.append(f"libellé de plus de {MAX_LABEL_CHARS} caractères")
    return problems


def _analysis(code: str) -> tuple[Flowchart | None, list[str]]:
    if any(_invisible(char) for char in code):
        return None, ["caractère invisible ou de contrôle interdit"]
    chart, problems = parse_flowchart(code)
    if chart is None:
        return None, problems
    problems = _chart_problems(chart)
    return (None if problems else chart), problems


def mermaid_problems(code: str) -> list[str]:
    """Problèmes du code (en français, pour la nouvelle demande au Scribe) ; vide s'il passe."""
    return _analysis(code)[1]


def _escaped(label: str) -> str:
    return "<br>".join(line.translate(_ESCAPES) for line in label.split("\n"))


class _Emitter:
    """Réécrit l'arbre : identifiants renumérotés, libellés échappés, une instruction par ligne."""

    def __init__(self, chart: Flowchart) -> None:
        self.chart = chart
        self.ids: dict[str, str] = {}
        self.declared: set[str] = set()
        self.subgraphs = {s.key for s in chart.statements if isinstance(s, Subgraph)}
        self.labels = {ref.key: ref.label for ref in _refs(chart) if ref.label is not None}
        self.shapes = {ref.key: ref.shape for ref in _refs(chart) if ref.shape is not None}

    def _id(self, key: str) -> str:
        return self.ids.setdefault(key, f"n{len(self.ids) + 1}")

    def _node(self, ref: NodeRef) -> str:
        ident = self._id(ref.key)
        if ref.key in self.declared or ref.key in self.subgraphs:
            return ident
        self.declared.add(ref.key)
        opening, closing = SHAPES[self.shapes.get(ref.key, RECTANGLE)]
        return f'{ident}{opening}"{_escaped(self.labels.get(ref.key, ref.key))}"{closing}'

    def _chain(self, chain: Chain) -> str:
        parts = [" & ".join(self._node(ref) for ref in chain.groups[0])]
        for edge, group in zip(chain.edges, chain.groups[1:], strict=True):
            label = "" if edge.label is None else f'|"{_escaped(edge.label)}"|'
            parts.append(edge.arrow + label)
            parts.append(" & ".join(self._node(ref) for ref in group))
        return " ".join(parts)

    def text(self) -> str:
        lines, depth = [f"flowchart {self.chart.direction}"], 1
        for statement in self.chart.statements:
            if isinstance(statement, End):
                depth -= 1
                lines.append("  " * depth + "end")
            elif isinstance(statement, Subgraph):
                title = statement.label if statement.label is not None else statement.key
                ident = self._id(statement.key)
                lines.append("  " * depth + f'subgraph {ident}["{_escaped(title)}"]')
                depth += 1
            elif isinstance(statement, Direction):
                lines.append("  " * depth + f"direction {statement.value}")
            else:
                lines.append("  " * depth + self._chain(statement))
        return "\n".join(lines)


def normalize_mermaid(code: str) -> str:
    """Le schéma réémis depuis l'arbre (la seule version qui sort du back) ; `ValueError` si le
    code ne passe pas (`mermaid_problems` non vide)."""
    chart, problems = _analysis(code)
    if chart is None:
        raise ValueError("; ".join(problems))
    return _Emitter(chart).text()
