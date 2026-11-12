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
- Arête : voir `mermaid_edges` (traits, pointillés, épaisses, longues ou à pointe double ;
  libellé `|...|` ou forme `-- texte -->`).
- Libellé : entre guillemets, ou sans guillemets s'il ne contient aucun caractère réservé.
  Entités Mermaid décodées, `<br>` (et `<br/>`) changé en saut de ligne, blancs réduits. Un
  libellé vide compte comme absent : le nœud garde son identifiant d'origine pour texte.
- Commentaires `%%` (ligne entière ou fin de ligne) : ignorés ; `%%{` (directive) : refusé.
- Une ligne de plus de `MAX_LINE_CHARS` caractères est refusée avant toute analyse ; toutes les
  expressions régulières sont sans retour arrière (possessives) : temps linéaire."""

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
# Instructions Mermaid hors grammaire, nommées dans le motif du refus pour aider le Scribe.
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
            return NodeRef(key, index, _label(cur, closing) or None)  # vide : l'identifiant
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
        return Subgraph(key, _label(cur, "]") or None)
    cur.pos = saved
    return Subgraph(key)


def _comment(cur: _Cursor) -> bool:
    """Commentaire `%%` jusqu'à la fin de la ligne (ignoré) ; `%%{` est une directive, refusée."""
    if not cur.text.startswith("%%", cur.pos):
        return False
    if "%%{" in cur.text[cur.pos :]:
        raise MermaidSyntaxError("directive `%%{` interdite")
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
        if len(text) > MAX_LINE_CHARS:
            problems.append(f"ligne {number} : plus de {MAX_LINE_CHARS} caractères")
            continue
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
