"""Filtre du Mermaid du Scribe (D85) : liste blanche. Seul un `flowchart` fait de nœuds, d'arêtes,
de libellés et de `subgraph` / `end` / `direction`, borné en taille, passe."""

import pytest

from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
)

VALID = 'flowchart TD\nA["Bases de Python"] --> B["API d\'un LLM"]\nB -->|ensuite| C(Projet)'
LEGIT = {
    "domain_map": (
        "flowchart TD\n"
        '  IA["Intelligence artificielle"] --> ML["Apprentissage automatique"]\n'
        '  ML --> DL["Réseaux de neurones"]\n'
        '  ML -->|"s\'appuie sur"| STATS["Statistiques"]\n'
        "  subgraph Produit\n"
        "    direction LR\n"
        '    API["API de LLM"] --- RAG["Recherche augmentée"]\n'
        "  end\n"
        "  DL --> API"
    ),
    "prerequisites": (
        "graph LR\n"
        'PY["Python"] --> HTTP["Appels HTTP"]; HTTP --> API["API de LLM"]\n'
        'API -- "avant" --> EVAL["Évaluation"]\n'
        "EVAL -.-> PROD{Mise en production}"
    ),
    "timeline": (
        "flowchart LR\n"
        'S1["Semaine 1 : bases<br>Python"] --> S2["Semaine 2 : API"]\n'
        'S2 --> S3["Semaine 3 : clic sur « click » dans un libellé"]\n'
        'S3 ==> P(("Projet final"))'
    ),
    "comparison": (
        "flowchart TD\n"
        'subgraph P1["Parcours pratique"]\n'
        '  A1["8 semaines"] --> B1["8 h par semaine"]\n'
        "end\n"
        'subgraph P2["Parcours socle"]\n'
        '  A2["12 semaines"] --> B2["6 h par semaine"]\n'
        "end\n"
        "P1 -. compare .- P2"
    ),
}


@pytest.mark.parametrize("kind", list(LEGIT))
def test_legitimate_boards_of_the_four_kinds_pass(kind: str) -> None:
    assert mermaid_problems(LEGIT[kind]) == []


def test_a_simple_flowchart_passes() -> None:
    assert mermaid_problems(VALID) == []
    assert mermaid_problems("graph LR\n  A --> B\n  subgraph S\n  B --> C\n  end") == []
    assert mermaid_problems('flowchart TD\nA["Début<br>du parcours"] --> B') == []
    assert mermaid_problems('flowchart TD\nA["a ; click B"] --> B') == []  # dans un libellé
    assert mermaid_problems('flowchart TD\nA["style ; class x"] --> B') == []
    assert mermaid_problems("flowchart TD\nclicker --> styled") == []  # identifiants voisins
    assert mermaid_problems('flowchart TD\nA["contact@exemple"] --> B') == []


@pytest.mark.parametrize(
    "code",
    [
        'flowchart TD\nA-->B\nclick A "https://x"',
        "%%{init: {}}%%\nflowchart TD\nA-->B",
        'flowchart TD\nA["<script>x</script>"]-->B',
        "sequenceDiagram\nA->>B: x",
        # Plusieurs instructions sur une ligne, séparées par `;` (revue 4.4).
        'flowchart TD\nA-->B; click A "https://evil.example"',
        "flowchart TD\nA-->B; click A call alert()",
        "flowchart TD\nA-->B;click A call alert()",
        "flowchart TD\nA-->B ;  CLICK A call alert()",
        "flowchart TD\nA-->B;;;click A call alert()",
        "flowchart TD\nA-->B;\tclick A call alert()",
        "flowchart TD\nA-->B\r\nclick A call alert()",
        "flowchart TD\nA-->B\rclick A call alert()",
        "flowchart TD\nA-->B click A call alert()",
        "flowchart TD\nA-->B\x85click A call alert()",
        "flowchart TD\nA-->B;​click A call alert()",
        "flowchart TD\nA-->B; click A call alert()",
        "flowchart TD\nA-->B; style A fill:url(https://evil.example/p.png)",
        "flowchart TD\nA-->B; STYLE A fill:URL (https://evil.example/p.png)",
        'flowchart TD\nA["url(https://evil.example)"] --> B',
        "flowchart TD\nA-->B; %%{init: {}}%%",
        # Guillemet isolé : il avalait la suite de la ligne (re-relecture 4.4).
        'flowchart TD\nA-->B"; click A "https://evil.example"',
        'flowchart TD\nA"-->B; click A call alert()',
        'flowchart TD\nA["x"]"-->B',
        # Styles et classes : interdits en entier (liste blanche).
        'flowchart TD\nA-->B; style A background:image-set("http://e")',
        "flowchart TD\nA-->B\nstyle A fill:#f9f",
        "flowchart TD\nA-->B\nstyle A background:\\75rl(x)",
        "flowchart TD\nA-->B\nclassDef c fill:#f9f\nclass A c",
        "flowchart TD\nA-->B\n\tClassDef c color:red",
        "flowchart TD\nA-->B\nlinkStyle 0 stroke:red",
        "flowchart TD\nA-->B\ncallback A alert",
        'flowchart TD\nA-->B\nhref A "https://x"',
        "flowchart TD\nA-->B\ninterpolate basis",
        "flowchart TD\nA-->B\n@import 'x.css'",
        'flowchart TD\nA@{ img: "https://evil.example/p.png", label: "x" } --> B',
        "flowchart TD\nA --> B@{ shape: rect }",
        # Entités Mermaid : `#60;` donne `<`, `#lt;` aussi.
        'flowchart TD\nA["#60;script#62;alert(1)#60;/script#62;"] --> B',
        'flowchart TD\nA["#lt;img src=x onerror=alert(1)#gt;"] --> B',
        'flowchart TD\nA["#quot;"] --> B',
    ],
)
def test_scribe_rejects_click_and_init_directives(code: str) -> None:
    assert mermaid_problems(code)


@pytest.mark.parametrize(
    "code",
    [
        'flowchart TD\nA["<img src=x onerror=alert(1)>"] --> B',
        'flowchart TD\nA["lien"] --> B\nB["javascript:alert(1)"]',
        "flowchart TD\nA[\"<a href='x'>a</a>\"] --> B",
        "flowchart TD\nA --> B\nstyle A fill:url(https://x/y.png)",
        "flowchart TD\nA --> B\nclassDef c background:url(x)",
        "flowchart TD\nA --> B\x0c",
        "",
        "flowchart\nA --> B",
        "pie\n'a' : 1",
    ],
)
def test_other_unsafe_or_malformed_codes_are_refused(code: str) -> None:
    assert mermaid_problems(code)


def test_size_limits() -> None:
    nodes = "\n".join(f"N{i} --> N{i + 1}" for i in range(MAX_NODES))
    assert any("nœuds" in p for p in mermaid_problems(f"flowchart TD\n{nodes}"))
    lines = "\n".join("A --> B" for _ in range(MAX_MERMAID_LINES))
    assert any("lignes" in p for p in mermaid_problems(f"flowchart TD\n{lines}"))
    label = "x" * (MAX_LABEL_CHARS + 1)
    assert any("libellé" in p for p in mermaid_problems(f'flowchart TD\nA["{label}"] --> B'))
    assert mermaid_problems(f'flowchart TD\nA["{"x" * MAX_LABEL_CHARS}"] --> B') == []


def test_edge_labels_are_not_counted_as_nodes() -> None:
    edges = "\n".join(f"N{i} -- relie --> N{i + 1}" for i in range(MAX_NODES - 1))
    assert mermaid_problems(f"flowchart TD\n{edges}") == []  # 40 nœuds, libellés à part
    assert mermaid_problems("flowchart LR\nA == mène à ==> B\nB -. puis .-> C") == []


def test_statements_after_a_semicolon_are_checked_like_lines() -> None:
    assert mermaid_problems("flowchart TD\nA-->B; B-->C") == []
    label = "x" * (MAX_LABEL_CHARS + 1)
    assert mermaid_problems(f'flowchart TD\nA-->B; C["{label}"]')
