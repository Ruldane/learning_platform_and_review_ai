"""Filtre du Mermaid du Scribe (D85) : seul un `flowchart` simple et borné passe."""

import pytest

from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
)

VALID = 'flowchart TD\nA["Bases de Python"] --> B["API d\'un LLM"]\nB -->|ensuite| C(Projet)'


def test_a_simple_flowchart_passes() -> None:
    assert mermaid_problems(VALID) == []
    assert mermaid_problems("graph LR\n  A --> B\n  subgraph S\n  B --> C\n  end") == []
    assert mermaid_problems('flowchart TD\nA["Début<br>du parcours"] --> B') == []


@pytest.mark.parametrize(
    "code",
    [
        'flowchart TD\nA-->B\nclick A "https://x"',
        "%%{init: {}}%%\nflowchart TD\nA-->B",
        'flowchart TD\nA["<script>x</script>"]-->B',
        "sequenceDiagram\nA->>B: x",
        # Plusieurs instructions sur une ligne, séparées par `;` (revue 4.4, Important 1).
        'flowchart TD\nA-->B; click A "https://evil.example"',
        "flowchart TD\nA-->B; click A call alert()",
        "flowchart TD\nA-->B;click A call alert()",
        "flowchart TD\nA-->B ;  CLICK A call alert()",
        "flowchart TD\nA-->B; style A fill:url(https://evil.example/p.png)",
        "flowchart TD\nA-->B; STYLE A fill:URL (https://evil.example/p.png)",
        'flowchart TD\nA["url(https://evil.example)"] --> B',
        "flowchart TD\nA-->B; %%{init: {}}%%",
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
    assert mermaid_problems('flowchart TD\nA["a ; click B"] --> B') == []  # dans un libellé
