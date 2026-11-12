"""Filtre du Mermaid du Scribe (SPEC 3.3, 17.4, D85) : le code vient d'un modèle qui a lu des
pages web, il est donc traité comme non fiable. Le Scribe n'a besoin que de nœuds, d'arêtes, de
libellés et de `subgraph` / `end` / `direction` : tout le reste est refusé (liste blanche).

- Première ligne `flowchart` (ou `graph`) `TD|LR|TB|RL`.
- Chaque ligne (tout séparateur de ligne compris : `\\r`, U+2028…) a un nombre pair de `"` : un
  guillemet isolé ne peut pas cacher la suite de la ligne.
- Aucune instruction (en tête de ligne ou après `;`, hors libellés entre guillemets) ne commence
  par `style`, `classDef`, `class`, `linkStyle`, `click`, `callback`, `href` ou `interpolate` ;
  aucun `%%{` (directive d'initialisation) ; aucun `@` hors libellé (métadonnées `A@{ img: … }`).
- Aucune entité Mermaid `#…;` (`#lt;`, `#60;` donneraient `<` ou `>`), aucune balise HTML hormis
  `<br>`, aucune adresse `javascript:`, aucun `href`, aucune ressource `url(`.
- Aucun caractère de contrôle ni de format invisible (hors tabulation et fins de ligne).
- Taille bornée : lignes, nœuds, longueur des libellés.

Le front rend en plus en `securityLevel: "strict"` : deux protections indépendantes."""

import re
import unicodedata

MAX_MERMAID_LINES = 80
MAX_NODES = 40
MAX_LABEL_CHARS = 80

_HEADER = re.compile(r"^(?:flowchart|graph)\s+(?:TD|LR|TB|RL)\s*;?\s*$")
_FORBIDDEN_STATEMENT = re.compile(
    r"^\s*(?:style|classDef|class|linkStyle|click|callback|href|interpolate)(?![\w-])",
    re.IGNORECASE,
)
_ENTITY = re.compile(r"#[A-Za-z0-9]+;")
_URL = re.compile(r"url\s*\(", re.IGNORECASE)
_TAG = re.compile(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9-]*)")
_ALLOWED_TAGS = {"br"}
_ALLOWED_CONTROLS = {"\t", "\n", "\r"}
_SKIPPED_LINE = re.compile(r"^\s*(?:%%|subgraph\b|end\b|direction\b)", re.IGNORECASE)
# Instructions d'une ligne aux guillemets appariés : morceaux séparés par `;`, hors chaînes.
_STATEMENT = re.compile(r'(?:[^;"]|"[^"]*")+')
# Libellés : chaînes entre guillemets, puis groupes entre crochets, parenthèses, accolades, barres.
_QUOTED = re.compile(r'"([^"]*)"')
_GROUPS = (
    re.compile(r"\[([^\[\]]*)\]"),
    re.compile(r"\(([^()]*)\)"),
    re.compile(r"\{([^{}]*)\}"),
    re.compile(r"\|([^|]*)\|"),
)
# Libellé d'arête sans délimiteurs : `A -- texte --> B`, `A == texte ==> B`, `A -. texte .-> B`.
_EDGE_TEXT = re.compile(r"(?<![-=.])(?:--|==|-\.)\s+([^-=.>|]+?)\s+(?:-->|==>|\.->|---|===)")
_CLASS_SUFFIX = re.compile(r":::[\w-]+")
_IDENTIFIER = re.compile(r"[A-Za-z_][\w]*")
_EDGE_WORDS = {"o", "x"}  # extrémités d'arêtes `--o`, `--x`


def _lines(code: str) -> list[str]:
    """Lignes non vides, découpées sur tout séparateur (`str.splitlines`) : plus large que celui
    de Mermaid, donc plus strict pour le contrôle des instructions."""
    return [line for line in code.splitlines() if line.strip()]


def _statements(lines: list[str]) -> list[str]:
    return [part for line in lines for part in _STATEMENT.findall(line) if part.strip()]


def _labels_and_rest(statement: str) -> tuple[list[str], str]:
    """Libellés de l'instruction et ce qui reste une fois les libellés retirés (identifiants,
    arêtes)."""
    labels = _QUOTED.findall(statement)
    rest = _QUOTED.sub(" ", statement)
    labels += _EDGE_TEXT.findall(rest)
    rest = _EDGE_TEXT.sub(" --> ", rest)
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


def _structure_problems(lines: list[str]) -> list[str]:
    if any(line.count('"') % 2 for line in lines):
        return ["guillemet isolé : les guillemets vont par paires sur une ligne"]
    statements = _statements(lines)
    if any(_FORBIDDEN_STATEMENT.match(s) for s in statements):
        return ["instruction interdite (`style`, `classDef`, `class`, `linkStyle`, `click`…)"]
    if any("@" in _QUOTED.sub(" ", s) for s in statements):
        return ["syntaxe `@` interdite hors libellé (`A@{ img: … }` charge une image)"]
    return []


def _invisible(char: str) -> bool:
    """Caractère de contrôle (hors tabulation et fins de ligne) ou de format (U+200B…) : il
    pourrait coller un mot-clé à ce qui précède sans que le filtre le voie comme un blanc."""
    return char not in _ALLOWED_CONTROLS and unicodedata.category(char) in ("Cc", "Cf")


def _content_problems(code: str) -> list[str]:
    problems: list[str] = []
    lowered = code.casefold()
    if any(_invisible(char) for char in code):
        problems.append("caractère invisible ou de contrôle interdit")
    if "%%{" in code:
        problems.append("directive d'initialisation `%%{` interdite")
    if _ENTITY.search(code):
        problems.append("entité `#…;` interdite")
    if "javascript:" in lowered or "href" in lowered:
        problems.append("lien interdit (`javascript:`, `href`)")
    tags = {match.group(1).casefold() for match in _TAG.finditer(code)}
    if tags - _ALLOWED_TAGS:
        problems.append("balise HTML interdite (seul `<br>` est admis)")
    if _URL.search(code):
        problems.append("ressource externe (`url(`) interdite")
    return problems


def _size_problems(lines: list[str]) -> list[str]:
    problems: list[str] = []
    if len(lines) > MAX_MERMAID_LINES:
        problems.append(f"plus de {MAX_MERMAID_LINES} lignes")
    nodes: set[str] = set()
    long_label = False
    for statement in _statements(lines[1:]):
        if _SKIPPED_LINE.match(statement):
            continue
        labels, rest = _labels_and_rest(statement)
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
    problems = _structure_problems(lines) + _content_problems(code)
    if not _HEADER.match(lines[0].strip()):
        problems.insert(0, "la première ligne doit être `flowchart TD` (ou LR, TB, RL)")
    return problems + _size_problems(lines)
