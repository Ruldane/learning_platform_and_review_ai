"""Filtre du Mermaid du Scribe (SPEC 3.3, 17.4, D85) : le code vient d'un modèle qui a lu des
pages web, il est donc traité comme non fiable. Seul un `flowchart` (ou `graph`) simple passe :
aucune directive d'initialisation (`%%{`), aucun `click` (liens, rappels JavaScript), aucun
HTML hormis le saut de ligne `<br>`, aucune adresse `javascript:` ni `href`, aucun style qui
charge une ressource (`url(`), et une taille bornée. Le front rend en plus en
`securityLevel: "strict"` : deux protections indépendantes."""

import re

MAX_MERMAID_LINES = 80
MAX_NODES = 40
MAX_LABEL_CHARS = 80

_HEADER = re.compile(r"^(?:flowchart|graph)\s+(?:TD|LR|TB|RL)\s*;?\s*$")
_CLICK = re.compile(r"^\s*click\b", re.IGNORECASE)
_TAG = re.compile(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9-]*)")
_ALLOWED_TAGS = {"br"}
_STYLE_LINE = re.compile(r"^\s*(?:style|classDef|linkStyle)\b", re.IGNORECASE)
_SKIPPED_LINE = re.compile(
    r"^\s*(?:%%|subgraph\b|end\b|direction\b|class\b|classDef\b|style\b|linkStyle\b)",
    re.IGNORECASE,
)
# Libellés : chaînes entre guillemets, puis groupes entre crochets, parenthèses, accolades, barres.
_QUOTED = re.compile(r'"([^"]*)"')
_GROUPS = (
    re.compile(r"\[([^\[\]]*)\]"),
    re.compile(r"\(([^()]*)\)"),
    re.compile(r"\{([^{}]*)\}"),
    re.compile(r"\|([^|]*)\|"),
)
_CLASS_SUFFIX = re.compile(r":::[\w-]+")
_IDENTIFIER = re.compile(r"[A-Za-z_][\w]*")
_EDGE_WORDS = {"o", "x"}  # extrémités d'arêtes `--o`, `--x`


def _lines(code: str) -> list[str]:
    return [line for line in code.splitlines() if line.strip()]


def _labels_and_rest(line: str) -> tuple[list[str], str]:
    """Libellés de la ligne et ce qui reste une fois les libellés retirés (identifiants,
    arêtes)."""
    labels = _QUOTED.findall(line)
    rest = _QUOTED.sub(" ", line)
    changed = True
    while changed:
        changed = False
        for group in _GROUPS:
            found = group.findall(rest)
            if found:
                labels.extend(found)
                rest = group.sub(" ", rest)
                changed = True
    return labels, _CLASS_SUFFIX.sub(" ", rest)


def _content_problems(code: str) -> list[str]:
    problems: list[str] = []
    lowered = code.casefold()
    if "%%{" in code:
        problems.append("directive d'initialisation `%%{` interdite")
    if any(_CLICK.match(line) for line in code.splitlines()):
        problems.append("directive `click` interdite")
    if "javascript:" in lowered or "href" in lowered:
        problems.append("lien interdit (`javascript:`, `href`)")
    tags = {match.group(1).casefold() for match in _TAG.finditer(code)}
    if tags - _ALLOWED_TAGS:
        problems.append("balise HTML interdite (seul `<br>` est admis)")
    if any(_STYLE_LINE.match(line) and "url(" in line.casefold() for line in code.splitlines()):
        problems.append("style qui charge une ressource (`url(`) interdit")
    return problems


def _size_problems(lines: list[str]) -> list[str]:
    problems: list[str] = []
    if len(lines) > MAX_MERMAID_LINES:
        problems.append(f"plus de {MAX_MERMAID_LINES} lignes")
    nodes: set[str] = set()
    long_label = False
    for line in lines[1:]:
        if _SKIPPED_LINE.match(line):
            continue
        labels, rest = _labels_and_rest(line)
        long_label = long_label or any(len(label.strip()) > MAX_LABEL_CHARS for label in labels)
        nodes.update(word for word in _IDENTIFIER.findall(rest) if word not in _EDGE_WORDS)
    if len(nodes) > MAX_NODES:
        problems.append(f"plus de {MAX_NODES} nœuds")
    if long_label:
        problems.append(f"libellé de plus de {MAX_LABEL_CHARS} caractères")
    return problems


def mermaid_problems(code: str) -> list[str]:
    """Problèmes du code (en français, pour la nouvelle demande au Scribe) ; vide s'il passe."""
    lines = _lines(code)
    if not lines:
        return ["schéma vide"]
    problems = _content_problems(code)
    if not _HEADER.match(lines[0].strip()):
        problems.insert(0, "la première ligne doit être `flowchart TD` (ou LR, TB, RL)")
    return problems + _size_problems(lines)
