"""Strict Mermaid grammar for the Scribe (SPEC 3.3, 17.4, D85 §11f).

The parser reports unsupported syntax. `mermaid_rules` serializes the parsed tree to keep
raw model output away from the renderer.

- Start with `flowchart` or `graph`, then `TD`, `TB`, `BT`, `LR`, or `RL` and an optional `;`.
- Statements occupy a line or are separated by `;` outside labels.
  - `subgraph <id>` with an optional `[...]` label
  - `end`
  - `direction <dir>`
  - Node groups such as `A & B` connected by edges
- Node IDs match `[A-Za-z][A-Za-z0-9_]{0,63}` with at most one shape from `SHAPES`.
- See `mermaid_edges` for solid, dotted, thick, long, and double-headed edges and their labels.
- Quote labels containing reserved characters. Mermaid entities are decoded, `<br>` and
  `<br/>` become newlines, and whitespace is collapsed. Empty labels fall back to the node ID.
- The parser ignores `%%` comments and rejects `%%{` directives.
- Lines longer than `MAX_LINE_CHARS` are rejected before parsing. Possessive regex quantifiers
  keep parsing linear.
"""

import re

from app.agents.nodes.mermaid_edges import edge_at
from app.agents.nodes.mermaid_tree import (
    SHAPES,
    Chain,
    Direction,
    Edge,
    End,
    Flowchart,
    MermaidSyntaxError,
    NodeRef,
    Statement,
    Subgraph,
    label_text,
)

MAX_LINE_CHARS = 400

KEYWORDS = frozenset({"subgraph", "end", "direction"})
# Include known unsupported instructions in diagnostics to help the Scribe revise.
FORBIDDEN = frozenset(
    {"click", "call", "callback", "href", "style", "classdef", "class", "linkstyle", "interpolate"}
    | {"acctitle", "accdescr"}
)
_RESERVED_IN_BARE_LABEL = set('"[](){}|')

_HEADER = re.compile(r"(?:flowchart|graph)[ \t]++(TD|TB|BT|LR|RL)[ \t]*+(?:;(.*+))?")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}+(?![A-Za-z0-9_])")
_DIRECTION = re.compile(r"(?:TD|TB|BT|LR|RL)(?![A-Za-z0-9_])")


class _Cursor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def done(self) -> bool:
        return self.pos >= len(self.text)

    def skip_blanks(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1

    def take(self, prefix: str) -> bool:
        if self.text.startswith(prefix, self.pos):
            self.pos += len(prefix)
            return True
        return False

    def match(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        found = pattern.match(self.text, self.pos)
        if found is not None:
            self.pos = found.end()
        return found

    def unexpected(self, expected: str) -> MermaidSyntaxError:
        if self.done():
            return MermaidSyntaxError(f"Expected {expected} at the end of the line")
        return MermaidSyntaxError(
            f'Expected {expected} before "{self.text[self.pos : self.pos + 16]}"'
        )


def _label(cur: _Cursor, closing: str) -> str:
    if cur.take('"'):
        end = cur.text.find('"', cur.pos)
        if end < 0:
            raise MermaidSyntaxError("Unclosed quote in a label")
        raw, cur.pos = cur.text[cur.pos : end], end + 1
        cur.skip_blanks()
        if not cur.take(closing):
            raise cur.unexpected(f"`{closing}`")
        return label_text(raw)
    end = cur.text.find(closing, cur.pos)
    if end < 0:
        raise MermaidSyntaxError(f"Unclosed label. Expected `{closing}`")
    raw = cur.text[cur.pos : end]
    if _RESERVED_IN_BARE_LABEL & set(raw):
        raise MermaidSyntaxError("Put labels containing reserved characters in quotes")
    cur.pos = end + len(closing)
    return label_text(raw)


def _identifier(cur: _Cursor, what: str) -> str:
    found = cur.match(_ID)
    if found is None:
        raise cur.unexpected(what)
    if found.group().casefold() in KEYWORDS:
        raise MermaidSyntaxError(f'Use a different node ID. "{found.group()}" is reserved')
    return found.group()


def _node(cur: _Cursor) -> NodeRef:
    key = _identifier(cur, "a node ID (ASCII letters, digits, or `_`)")
    for index, (opening, closing) in enumerate(SHAPES):
        if cur.take(opening):
            return NodeRef(key, index, _label(cur, closing) or None)
    return NodeRef(key)


def _group(cur: _Cursor) -> list[NodeRef]:
    nodes = [_node(cur)]
    while True:
        saved = cur.pos
        cur.skip_blanks()
        if not cur.take("&"):
            cur.pos = saved
            return nodes
        cur.skip_blanks()
        nodes.append(_node(cur))


def _edge(cur: _Cursor) -> Edge | None:
    saved = cur.pos
    cur.skip_blanks()
    found = edge_at(cur.text, cur.pos)
    if found is None:
        cur.pos = saved
        return None
    edge, cur.pos = found
    return edge


def _chain(cur: _Cursor) -> Chain:
    groups, edges = [_group(cur)], []
    while (edge := _edge(cur)) is not None:
        cur.skip_blanks()
        edges.append(edge)
        groups.append(_group(cur))
    return Chain(groups, edges)


def _blank_then(cur: _Cursor) -> None:
    if not cur.take(" ") and not cur.take("\t"):
        raise cur.unexpected("whitespace")
    cur.skip_blanks()


def _statement(cur: _Cursor) -> Statement:
    found = _ID.match(cur.text, cur.pos)
    word = found.group().casefold() if found is not None else ""
    if word in FORBIDDEN:
        raise MermaidSyntaxError(
            f"The `{found.group() if found else word}` instruction is forbidden. "
            "Use nodes, edges, `subgraph`, `end`, and `direction`"
        )
    if found is None or word not in KEYWORDS:
        return _chain(cur)
    cur.pos = found.end()
    if word == "end":
        return End()
    _blank_then(cur)
    if word == "direction":
        value = cur.match(_DIRECTION)
        if value is None:
            raise cur.unexpected("a direction (TD, TB, BT, LR, or RL)")
        return Direction(value.group())
    key = _identifier(cur, "a subgraph ID")
    saved = cur.pos
    cur.skip_blanks()
    if cur.take("["):
        return Subgraph(key, _label(cur, "]") or None)
    cur.pos = saved
    return Subgraph(key)


def _comment(cur: _Cursor) -> bool:
    """Recognize a `%%` line comment and reject any `%%{` directive in it."""
    if not cur.text.startswith("%%", cur.pos):
        return False
    if "%%{" in cur.text[cur.pos :]:
        raise MermaidSyntaxError("The `%%{` directive is forbidden")
    return True


def _parse_line(text: str, chart: Flowchart) -> None:
    cur = _Cursor(text)
    while True:
        cur.skip_blanks()
        if cur.done() or _comment(cur):
            return
        if cur.take(";"):
            continue
        chart.statements.append(_statement(cur))
        cur.skip_blanks()
        if not cur.done() and not cur.take(";") and not _comment(cur):
            raise cur.unexpected("`;` or a line break")


def _balance_problems(statements: list[Statement]) -> list[str]:
    depth = 0
    for statement in statements:
        if isinstance(statement, Subgraph):
            depth += 1
        elif isinstance(statement, End):
            if depth == 0:
                return ["`end` without an open `subgraph`"]
            depth -= 1
    return ["Close each `subgraph` with `end`"] if depth else []


def parse_flowchart(code: str) -> tuple[Flowchart | None, list[str]]:
    """Return the parsed chart or a list of syntax problems."""
    chart: Flowchart | None = None
    problems: list[str] = []
    for number, line in enumerate(code.splitlines(), start=1):
        text = line.strip()
        if len(text) > MAX_LINE_CHARS:
            problems.append(f"Line {number}: exceeds {MAX_LINE_CHARS} characters")
            continue
        if text.startswith("%%"):
            if "%%{" in text:
                problems.append(f"Line {number}: the `%%{{` directive is forbidden")
            continue
        if not text:
            continue
        if chart is None:
            header = _HEADER.fullmatch(text)
            if header is None:
                return None, ["Start with `flowchart TD` or use TB, BT, LR, or RL"]
            chart, text = Flowchart(header.group(1)), header.group(2) or ""
        try:
            _parse_line(text, chart)
        except MermaidSyntaxError as exc:
            problems.append(f"Line {number}: {exc}")
    if chart is None:
        return None, problems or ["The diagram is empty"]
    problems += _balance_problems(chart.statements)
    return (None if problems else chart), problems
