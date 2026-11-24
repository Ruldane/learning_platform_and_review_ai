"""Normalize untrusted Mermaid from the Scribe (SPEC 3.3, 17.4, D85 §11f).

Parse the chart with the strict grammar and emit Mermaid from the resulting tree.
IDs are assigned in order of first appearance. Each node declares its shape and quoted
label on first use. Labels use entity escapes and emit only `<br>` as HTML. Each statement
occupies one line, with subgraph contents indented.

The board event, port, and PDF (4.8) use the normalized version. Limits apply to lines,
nodes, and label lengths. Invisible format and control characters are rejected.
"""

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
MAX_CODE_CHARS = 8000

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
        # Escape colons to prevent icon handling and Mermaid's style rule that strips
        # the trailing semicolon from an entity.
        ":": "#58;",
    }
)


def _invisible(char: str) -> bool:
    """Detect a control or format character other than tabs and line breaks."""
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
        problems.append("A label contains an invisible or control character")
    if len(chart.statements) + 1 > MAX_MERMAID_LINES:
        problems.append(f"The diagram exceeds {MAX_MERMAID_LINES} lines")
    subgraphs = {s.key for s in chart.statements if isinstance(s, Subgraph)}
    nodes = {ref.key for ref in _refs(chart)} - subgraphs
    if not nodes:
        problems.append("Add at least one node")
    if len(nodes) > MAX_NODES:
        problems.append(f"The diagram exceeds {MAX_NODES} nodes")
    if any(len(label) > MAX_LABEL_CHARS for label in labels):
        problems.append(f"A label exceeds {MAX_LABEL_CHARS} characters")
    return problems


def _analysis(code: str) -> tuple[Flowchart | None, list[str]]:
    if len(code) > MAX_CODE_CHARS:  # Apply the size limit before parsing for every caller.
        return None, [f"The diagram exceeds {MAX_CODE_CHARS} characters"]
    if any(_invisible(char) for char in code):
        return None, ["The diagram contains an invisible or control character"]
    chart, problems = parse_flowchart(code)
    if chart is None:
        return None, problems
    problems = _chart_problems(chart)
    return (None if problems else chart), problems


def mermaid_problems(code: str) -> list[str]:
    """Return diagnostics for the Scribe to revise, or an empty list for valid code."""
    return _analysis(code)[1]


def _escaped(label: str) -> str:
    return "<br>".join(line.translate(_ESCAPES) for line in label.split("\n"))


class _Emitter:
    """Emit statements with reassigned IDs, escaped labels, and one statement per line."""

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
    """Return the normalized diagram. Raise `ValueError` when validation fails."""
    chart, problems = _analysis(code)
    if chart is None:
        raise ValueError("; ".join(problems))
    return _Emitter(chart).text()
