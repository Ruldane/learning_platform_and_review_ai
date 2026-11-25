"""Parse the Scribe's Mermaid edges in linear time (D85 §11f).

Disjoint character classes and possessive quantifiers prevent backtracking. The closing
arrow of a labeled edge matches only at the start of a run of `-`, `.`, or `=`.

- Solid edges use two to eight dashes with an arrowhead or three to eight dashes alone.
- Dotted edges such as `-.->` and `-.-` use one to four dots.
- Thick edges use `==>`, `===`, and their longer forms.
- Double-headed edges use `<-->`, `<-.->`, or `<==>`.
- Labels follow an edge as `|text|` or appear within it as `-- text -->`, `-. text .->`, or
  `== text ==>`. Text can contain standalone dashes, dots, and equals signs. Quote labels
  or omit reserved characters such as `"`, `|`, and `;`.
"""

import re

from app.agents.nodes.mermaid_tree import Edge, MermaidSyntaxError, label_text

MAX_RUN = 8
_SOLID = re.compile(r"(<?)(-{2,8}+)(>?)")
_DOTTED = re.compile(r"(<?)-(\.{1,4}+)-(>?)")
_THICK = re.compile(r"(<?)(={2,8}+)(>?)")
_PIPE = re.compile(r'[ \t]*+\|(?:"([^"]*+)"|([^"|]*+))\|')
# Match the closing pattern for each opener only at the beginning of a run.
_CLOSERS = {
    "--": re.compile(r"(?<!-)(-{2,}+)(>?)"),
    "-.": re.compile(r"(?<!\.)(\.++)-(>?)"),
    "==": re.compile(r"(?<!=)(={2,}+)(>?)"),
}
_QUOTED_TEXT = re.compile(r'[ \t]*+"([^"]*+)"[ \t]*+')
_FORBIDDEN_IN_BARE_TEXT = set('"|;')


def _arrow(text: str, pos: int) -> tuple[str, int] | None:
    """Return the arrow and end position of an unlabeled edge at `pos`, if present."""
    for pattern in (_DOTTED, _SOLID, _THICK):
        found = pattern.match(text, pos)
        if found is None:
            continue
        left, run, right = found.groups()
        dotted = pattern is _DOTTED
        if (left and not right) or (not dotted and len(run) < 3 and not right):
            return None  # A left head needs a right head. Bare `--` and `==` open labels.
        return left + (f"-{run}-" if dotted else run) + right, found.end()
    return None


def _closing(opener: str, found: re.Match[str]) -> str | None:
    """Return the closing arrow when the matched run ends the edge label."""
    run, head = found.group(1), found.group(2)
    if opener == "-.":
        return f"-{run}-{head}" if len(run) <= 4 else None
    if len(run) > MAX_RUN or (len(run) < 3 and not head):
        return None
    return run + head


def _bare_text(raw: str) -> str | None:
    text = raw.strip()
    if not text or _FORBIDDEN_IN_BARE_TEXT & set(text):
        raise MermaidSyntaxError(
            'Use `-->|"text"|` for empty edge text or text containing `"`, `|`, or `;`'
        )
    return label_text(text) or None


def _text_edge(text: str, pos: int) -> tuple[Edge, int] | None:
    opener = text[pos : pos + 2]
    pattern = _CLOSERS.get(opener)
    if pattern is None:
        return None
    quoted = _QUOTED_TEXT.match(text, pos + 2)
    if quoted is not None:  # A quoted label must be followed immediately by a closer.
        found = pattern.match(text, quoted.end())
        arrow = None if found is None else _closing(opener, found)
        if found is None or arrow is None:
            return None
        return Edge(arrow, label_text(quoted.group(1)) or None), found.end()
    for found in pattern.finditer(text, pos + 2):
        arrow = _closing(opener, found)
        if arrow is not None:
            return Edge(arrow, _bare_text(text[pos + 2 : found.start()])), found.end()
    return None


def edge_at(text: str, pos: int) -> tuple[Edge, int] | None:
    """Return the edge at `pos` and its end position, if present."""
    plain = _arrow(text, pos)
    if plain is None:
        return _text_edge(text, pos)
    arrow, end = plain
    pipe = _PIPE.match(text, end)
    if pipe is None:
        return Edge(arrow), end
    raw = pipe.group(1) if pipe.group(1) is not None else pipe.group(2)
    return Edge(arrow, label_text(raw) or None), pipe.end()
