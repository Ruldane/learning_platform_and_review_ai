"""Arêtes du Mermaid du Scribe (D85 §11f), lues **sans retour arrière**. Chaque motif est fait
de classes disjointes et de quantificateurs possessifs. La fin d'une arête à texte n'est
cherchée qu'au début d'une suite de `-`, `.` ou `=`. L'analyse reste ainsi linéaire
(re-relecture 3 : `A -- ` suivi de milliers d'espaces bloquait la boucle d'événements).

- Arêtes :
  - traits : `-->`, `--->`… (2 à 8 traits et une pointe), `---`, `----`… (3 à 8 traits) ;
  - pointillés : `-.->`, `-..->`, `-.-` (1 à 4 points) ;
  - épaisses : `==>`, `===`… ;
  - pointe double : `<-->`, `<-.->`, `<==>`.
- Libellé : `|…|` après l'arête, ou forme à texte `-- texte -->`, `-. texte .->`, `== texte ==>`.
  Le texte peut contenir des `-`, `.` ou `=` isolés (`pré-requis`, `v1.2`). Il est entre
  guillemets, ou sans `"`, `|` ni `;`."""

import re

from app.agents.nodes.mermaid_tree import Edge, MermaidSyntaxError, label_text

MAX_RUN = 8
_SOLID = re.compile(r"(<?)(-{2,8}+)(>?)")
_DOTTED = re.compile(r"(<?)-(\.{1,4}+)-(>?)")
_THICK = re.compile(r"(<?)(={2,8}+)(>?)")
_PIPE = re.compile(r'[ \t]*+\|(?:"([^"]*+)"|([^"|]*+))\|')
# Fins d'une arête à texte, par ouvrant ; seulement au début d'une suite (lookbehind).
_CLOSERS = {
    "--": re.compile(r"(?<!-)(-{2,}+)(>?)"),
    "-.": re.compile(r"(?<!\.)(\.++)-(>?)"),
    "==": re.compile(r"(?<!=)(={2,}+)(>?)"),
}
_QUOTED_TEXT = re.compile(r'[ \t]*+"([^"]*+)"[ \t]*+')
_FORBIDDEN_IN_BARE_TEXT = set('"|;')


def _arrow(text: str, pos: int) -> tuple[str, int] | None:
    """Une arête sans texte à `pos` (forme rendue, fin) ; `None` si ce n'en est pas une."""
    for pattern in (_DOTTED, _SOLID, _THICK):
        found = pattern.match(text, pos)
        if found is None:
            continue
        left, run, right = found.groups()
        dotted = pattern is _DOTTED
        if (left and not right) or (not dotted and len(run) < 3 and not right):
            return None  # `<--` sans pointe ; `--` et `==` seuls ouvrent une arête à texte
        return left + (f"-{run}-" if dotted else run) + right, found.end()
    return None


def _closing(opener: str, found: re.Match[str]) -> str | None:
    """L'arête que ferme `found`, ou `None` si cette suite fait partie du texte."""
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
            'texte d\'arête vide ou avec `"`, `|` ou `;` : écris plutôt `-->|"texte"|`'
        )
    return label_text(text) or None


def _text_edge(text: str, pos: int) -> tuple[Edge, int] | None:
    opener = text[pos : pos + 2]
    pattern = _CLOSERS.get(opener)
    if pattern is None:
        return None
    quoted = _QUOTED_TEXT.match(text, pos + 2)
    if quoted is not None:  # `-- "texte" -->` : la fin n'est cherchée qu'après le guillemet
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
    """L'arête qui commence à `pos` et sa fin, ou `None` s'il n'y en a pas."""
    plain = _arrow(text, pos)
    if plain is None:
        return _text_edge(text, pos)
    arrow, end = plain
    pipe = _PIPE.match(text, end)
    if pipe is None:
        return Edge(arrow), end
    raw = pipe.group(1) if pipe.group(1) is not None else pipe.group(2)
    return Edge(arrow, label_text(raw) or None), pipe.end()
