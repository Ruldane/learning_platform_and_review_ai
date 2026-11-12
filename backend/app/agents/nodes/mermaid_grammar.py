"""Grammaire stricte du Mermaid du Scribe (SPEC 3.3, 17.4, D85 §11f). L'analyseur n'admet
qu'un `flowchart` fait de nœuds, d'arêtes, de libellés et de `subgraph` / `end` / `direction`.
Tout le reste est refusé avec un motif lisible. `mermaid_rules` réémet ensuite le schéma depuis
l'arbre : le texte du modèle ne sort jamais.

- En-tête : `flowchart` ou `graph`, puis `TD`, `TB`, `BT`, `LR` ou `RL` (suivi de `;` admis).
- Instructions : une ligne, ou des morceaux de ligne séparés par `;` hors libellés.
  - `subgraph <id>`, avec un libellé facultatif `[...]` ;
  - `end` ;
  - `direction <dir>` ;
  - une chaîne de groupes de nœuds `A & B` reliés par des arêtes.
- Nœud : identifiant `[A-Za-z][A-Za-z0-9_]{0,63}`, suivi au plus d'une forme connue (`SHAPES`).
- Arête : `-->`, `---`, `-.->`, `-.-`, `==>`, `===`. Libellé facultatif `|...|`, ou forme
  `-- texte -->` (et `-. texte .->`, `== texte ==>`).
- Libellé : entre guillemets, ou sans guillemets s'il ne contient aucun caractère réservé.
  Entités Mermaid décodées, `<br>` (et `<br/>`) changé en saut de ligne, blancs réduits.
- Commentaires `%%` sur leur propre ligne : ignorés ; `%%{` (directive) : refusé."""

import re

from app.agents.nodes.mermaid_tree import (
    SHAPES,
    Chain,
    Direction,
    Edge,
    End,
    Flowchart,
    NodeRef,
    Statement,
    Subgraph,
    label_text,
)

KEYWORDS = frozenset({"subgraph", "end", "direction"})
# Instructions Mermaid hors grammaire, nommées dans le motif du refus pour aider le Scribe.
FORBIDDEN = frozenset(
    {"click", "call", "callback", "href", "style", "classdef", "class", "linkstyle", "interpolate"}
    | {"acctitle", "accdescr"}
)
ARROWS = ("-.->", "-.-", "-->", "---", "==>", "===")
_RESERVED_IN_BARE_LABEL = set('"[](){}|')

_HEADER = re.compile(r"(?:flowchart|graph)[ \t]+(TD|TB|BT|LR|RL)[ \t]*(?:;(.*))?")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}(?![A-Za-z0-9_])")
_DIRECTION = re.compile(r"(?:TD|TB|BT|LR|RL)(?![A-Za-z0-9_])")
_PIPE = re.compile(r'[ \t]*\|(?:"([^"]*)"|([^"|]*))\|')
_TEXT_EDGES = (
    (
        re.compile(r'--[ \t]*(?:"([^"]*)"|([^"|;\-]+?))[ \t]*(-->|---)'),
        {"-->": "-->", "---": "---"},
    ),
    (
        re.compile(r'-\.[ \t]*(?:"([^"]*)"|([^"|;.]+?))[ \t]*(\.->|\.-)'),
        {".->": "-.->", ".-": "-.-"},
    ),
    (re.compile(r'==[ \t]*(?:"([^"]*)"|([^"|;=]+?))[ \t]*(==>|===)'), {"==>": "==>", "===": "==="}),
)


class MermaidSyntaxError(ValueError):
    """Une instruction hors grammaire ; le message est le motif rendu au Scribe."""


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
            return MermaidSyntaxError(f"{expected} attendu en fin de ligne")
        return MermaidSyntaxError(
            f"{expected} attendu avant « {self.text[self.pos : self.pos + 16]} »"
        )


def _label(cur: _Cursor, closing: str) -> str:
    if cur.take('"'):
        end = cur.text.find('"', cur.pos)
        if end < 0:
            raise MermaidSyntaxError("guillemet non fermé dans un libellé")
        raw, cur.pos = cur.text[cur.pos : end], end + 1
        cur.skip_blanks()
        if not cur.take(closing):
            raise cur.unexpected(f"`{closing}`")
        return label_text(raw)
    end = cur.text.find(closing, cur.pos)
    if end < 0:
        raise MermaidSyntaxError(f"libellé non fermé (`{closing}` attendu)")
    raw = cur.text[cur.pos : end]
    if _RESERVED_IN_BARE_LABEL & set(raw):
        raise MermaidSyntaxError("libellé avec un caractère réservé : mets-le entre guillemets")
    cur.pos = end + len(closing)
    return label_text(raw)


def _identifier(cur: _Cursor, what: str) -> str:
    found = cur.match(_ID)
    if found is None:
        raise cur.unexpected(what)
    if found.group().casefold() in KEYWORDS:
        raise MermaidSyntaxError(f"« {found.group()} » est réservé : il ne nomme pas un nœud")
    return found.group()


def _node(cur: _Cursor) -> NodeRef:
    key = _identifier(cur, "identifiant de nœud (lettres ASCII, chiffres, `_`)")
    for index, (opening, closing) in enumerate(SHAPES):
        if cur.take(opening):
            return NodeRef(key, index, _label(cur, closing))
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


def _optional(text: str) -> str | None:
    return label_text(text) or None


def _edge(cur: _Cursor) -> Edge | None:
    saved = cur.pos
    cur.skip_blanks()
    for arrow in ARROWS:
        if cur.take(arrow):
            pipe = cur.match(_PIPE)
            raw = (
                None
                if pipe is None
                else (pipe.group(1) if pipe.group(1) is not None else pipe.group(2))
            )
            return Edge(arrow, None if raw is None else _optional(raw))
    for pattern, arrows in _TEXT_EDGES:
        found = cur.match(pattern)
        if found is not None:
            raw = found.group(1) if found.group(1) is not None else found.group(2)
            return Edge(arrows[found.group(3)], _optional(raw))
    cur.pos = saved
    return None


def _chain(cur: _Cursor) -> Chain:
    groups, edges = [_group(cur)], []
    while (edge := _edge(cur)) is not None:
        cur.skip_blanks()
        edges.append(edge)
        groups.append(_group(cur))
    return Chain(groups, edges)


def _blank_then(cur: _Cursor) -> None:
    if not cur.take(" ") and not cur.take("\t"):
        raise cur.unexpected("un blanc")
    cur.skip_blanks()


def _statement(cur: _Cursor) -> Statement:
    found = _ID.match(cur.text, cur.pos)
    word = found.group().casefold() if found is not None else ""
    if word in FORBIDDEN:
        raise MermaidSyntaxError(
            f"instruction `{found.group() if found else word}` interdite : seulement des nœuds, "
            "des arêtes, `subgraph`, `end` et `direction`"
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
            raise cur.unexpected("direction (TD, TB, BT, LR ou RL)")
        return Direction(value.group())
    key = _identifier(cur, "identifiant du sous-graphe")
    saved = cur.pos
    cur.skip_blanks()
    if cur.take("["):
        return Subgraph(key, _label(cur, "]"))
    cur.pos = saved
    return Subgraph(key)


def _parse_line(text: str, chart: Flowchart) -> None:
    cur = _Cursor(text)
    while True:
        cur.skip_blanks()
        if cur.done():
            return
        if cur.take(";"):
            continue
        chart.statements.append(_statement(cur))
        cur.skip_blanks()
        if not cur.done() and not cur.take(";"):
            raise cur.unexpected("`;` ou une fin de ligne")


def _balance_problems(statements: list[Statement]) -> list[str]:
    depth = 0
    for statement in statements:
        if isinstance(statement, Subgraph):
            depth += 1
        elif isinstance(statement, End):
            if depth == 0:
                return ["`end` sans `subgraph` ouvert"]
            depth -= 1
    return ["`subgraph` non fermé par `end`"] if depth else []


def parse_flowchart(code: str) -> tuple[Flowchart | None, list[str]]:
    """L'arbre du schéma et la liste des problèmes (l'arbre est `None` s'il y en a)."""
    chart: Flowchart | None = None
    problems: list[str] = []
    for number, line in enumerate(code.splitlines(), start=1):
        text = line.strip()
        if text.startswith("%%"):
            if "%%{" in text:
                problems.append(f"ligne {number} : directive `%%{{` interdite")
            continue
        if not text:
            continue
        if chart is None:
            header = _HEADER.fullmatch(text)
            if header is None:
                return None, ["la première ligne doit être `flowchart TD` (ou TB, BT, LR, RL)"]
            chart, text = Flowchart(header.group(1)), header.group(2) or ""
        try:
            _parse_line(text, chart)
        except MermaidSyntaxError as exc:
            problems.append(f"ligne {number} : {exc}")
    if chart is None:
        return None, problems or ["schéma vide"]
    problems += _balance_problems(chart.statements)
    return (None if problems else chart), problems
