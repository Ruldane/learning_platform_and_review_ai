"""Mermaid du Scribe (D85 §11f) : grammaire stricte puis réémission. Seul un `flowchart` fait de
nœuds, d'arêtes, de libellés et de `subgraph` / `end` / `direction` passe ; la sortie est
régénérée (identifiants `n1`…, libellés entre guillemets, texte échappé par nos entités)."""

import pytest

from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
    normalize_mermaid,
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
    once = normalize_mermaid(LEGIT[kind])
    assert normalize_mermaid(once) == once  # aller-retour


def test_normalized_output_is_regenerated_from_the_tree() -> None:
    assert normalize_mermaid(LEGIT["comparison"]) == (
        "flowchart TD\n"
        '  subgraph n1["Parcours pratique"]\n'
        '    n2["8 semaines"] --> n3["8 h par semaine"]\n'
        "  end\n"
        '  subgraph n4["Parcours socle"]\n'
        '    n5["12 semaines"] --> n6["6 h par semaine"]\n'
        "  end\n"
        '  n1 -.-|"compare"| n4'
    )
    assert normalize_mermaid("graph LR\nA-->B; B-->C\nA[Début<BR/>fin]") == (
        'flowchart LR\n  n1["Début<br>fin"] --> n2["B"]\n  n2 --> n3["C"]\n  n1'
    )


def test_every_shape_and_arrow_is_kept() -> None:
    code = (
        "flowchart LR\nA([a]) --> B[[b]] -.-> C[(c)] ==> D((d))\n"
        "D --- E{e} -.- F{{f}} === G>g]\nA & B -- texte --> G\nC == fort ==> D"
    )
    assert normalize_mermaid(code) == (
        "flowchart LR\n"
        '  n1(["a"]) --> n2[["b"]] -.-> n3[("c")] ==> n4(("d"))\n'
        '  n4 --- n5{"e"} -.- n6{{"f"}} === n7>"g"]\n'
        '  n1 & n2 -->|"texte"| n7\n'
        '  n3 ==>|"fort"| n4'
    )


@pytest.mark.parametrize(
    ("label", "escaped"),
    [
        ("x < y", "x #lt; y"),
        ("List<String>", "List#lt;String#gt;"),
        ("JavaScript: les bases", "JavaScript#58; les bases"),
        ("attribut href", "attribut href"),
        ("url(), image-set()", "url(), image-set()"),
        ("a & b, 50 %, #1", "a #amp; b, 50 #37;, #35;1"),
        ("a ; click B", "a ; click B"),
        ("contact@exemple", "contact@exemple"),
        ("`**gras**`", "#96;**gras**#96;"),
        (
            "a<br style=background:image-set('//e/a')>b",
            "a#lt;br style=background#58;image-set('//e/a')#gt;b",
        ),
        ("<img src=x onerror=alert(1)>", "#lt;img src=x onerror=alert(1)#gt;"),
        ("#60;script#62;", "#lt;script#gt;"),
        ("#quot;; click A #quot;https://e#quot;", "#quot;; click A #quot;https#58;//e#quot;"),
        ("%%{init}%%", "#37;#37;{init}#37;#37;"),
    ],
)
def test_label_text_is_escaped_by_our_own_entities(label: str, escaped: str) -> None:
    code = f'flowchart TD\nA["{label}"] -->|"{label}"| B'
    assert mermaid_problems(code) == []
    out = normalize_mermaid(code)
    assert out == f'flowchart TD\n  n1["{escaped}"] -->|"{escaped}"| n2["B"]'
    assert normalize_mermaid(out) == out
    assert "<" not in out.replace("<br>", "")


@pytest.mark.parametrize(
    "code",
    [
        # Re-relecture 2 : `"` collé à un identifiant, `click` caché dans un « libellé ».
        'flowchart TD\nA --> B"; click A "https://evil.example"; C"',
        'flowchart TD\nA -->|suite| B"; click A "https://evil.example"; C"',
        'flowchart TD\nsubgraph S\nA --> B"; click A "https://evil.example"; C"\nend',
        # Re-relecture du round 1 et variantes.
        'flowchart TD\nA-->B"; click A "https://evil.example"',
        'flowchart TD\nA"-->B; click A call alert()',
        'flowchart TD\nA["x"]"-->B',
        'flowchart TD\nA-->B\nclick A "https://x"',
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
        "flowchart TD\nA-->Bclick A",
        # Directives, styles, classes, métadonnées : hors grammaire.
        "%%{init: {}}%%\nflowchart TD\nA-->B",
        "flowchart TD\nA-->B; %%{init: {}}%%",
        "flowchart TD\nA-->B\n%%{init: {}}%%",
        'flowchart TD\nA-->B; style A background:image-set("http://e")',
        "flowchart TD\nA-->B\nstyle A fill:url(https://evil.example/p.png)",
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
        "flowchart TD\nA:::hidden --> B",
        "flowchart TD\naccTitle: x",
        # Identifiants : ASCII seulement, jamais un mot réservé.
        "flowchart TD\nÉtape --> B",
        "flowchart TD\nｃlick --> B",
        "flowchart TD\nA --> end",
        "flowchart TD\nA-B --> C",
        # Autres types et en-têtes.
        "sequenceDiagram\nA->>B: x",
        "pie\n'a' : 1",
        "flowchart\nA --> B",
        "",
        "flowchart TD",
        "flowchart TD\nA --> B\x0c",
        'flowchart TD\nA["#8203;"] --> B',  # entité qui donne un caractère invisible
        # Structure.
        "flowchart TD\nA ----------> B",  # plus de 8 traits
        "flowchart TD\nA <-- B",  # pointe double sans seconde pointe
        "flowchart TD\nA -- texte B",
        'flowchart TD\nA -- a; click A "x" --> B',
        "flowchart TD\nA -- --> B",
        "flowchart TD\nA --> B %%{init: {}}%%",
        "flowchart TD\nA" + " " * 400 + "--> B",  # ligne trop longue
        'flowchart TD\nA["non fermé] --> B',
        "flowchart TD\nA[a(b)] --> B",
        "flowchart TD\nsubgraph S\nA --> B",
        "flowchart TD\nA --> B\nend",
    ],
)
def test_anything_outside_the_grammar_is_refused(code: str) -> None:
    assert mermaid_problems(code)
    with pytest.raises(ValueError):
        normalize_mermaid(code)


def test_refusals_name_the_line_and_the_forbidden_instruction() -> None:
    problems = mermaid_problems("flowchart TD\nA --> B\nclick A call alert()")
    assert problems == [
        "ligne 3 : instruction `click` interdite : seulement des nœuds, des arêtes, `subgraph`, "
        "`end` et `direction`"
    ]
    assert mermaid_problems('flowchart TD\nA --> B"')[0].startswith("ligne 2 : ")


def test_comments_are_dropped() -> None:
    assert normalize_mermaid("%% carte\nflowchart TD\n%% nœuds\nA --> B") == (
        'flowchart TD\n  n1["A"] --> n2["B"]'
    )


def test_last_label_and_shape_of_a_node_win() -> None:
    code = 'flowchart TD\nA --> B\nA(("Bases"))'
    assert normalize_mermaid(code) == 'flowchart TD\n  n1(("Bases")) --> n2["B"]\n  n1'


def test_size_limits() -> None:
    nodes = "\n".join(f"N{i} --> N{i + 1}" for i in range(MAX_NODES))
    assert any("nœuds" in p for p in mermaid_problems(f"flowchart TD\n{nodes}"))
    lines = "\n".join("A --> B" for _ in range(MAX_MERMAID_LINES))
    assert any("lignes" in p for p in mermaid_problems(f"flowchart TD\n{lines}"))
    statements = ("A-->B;" * 40 + "\n") * 2
    assert any("lignes" in p for p in mermaid_problems("flowchart TD\n" + statements))
    assert any("caractères" in p for p in mermaid_problems("flowchart TD\n" + "A-->B;" * 80))
    label = "x" * (MAX_LABEL_CHARS + 1)
    assert any("libellé" in p for p in mermaid_problems(f'flowchart TD\nA["{label}"] --> B'))
    assert mermaid_problems(f'flowchart TD\nA["{"x" * MAX_LABEL_CHARS}"] --> B') == []


def test_edge_labels_are_not_counted_as_nodes() -> None:
    edges = "\n".join(f"N{i} -- relie --> N{i + 1}" for i in range(MAX_NODES - 1))
    assert mermaid_problems(f"flowchart TD\n{edges}") == []  # 40 nœuds, libellés à part
    assert mermaid_problems("flowchart LR\nA == mène à ==> B\nB -. puis .-> C") == []


def test_simple_valid_code_passes() -> None:
    assert mermaid_problems(VALID) == []
    assert mermaid_problems("flowchart TD\nclicker --> styled") == []  # identifiants voisins
    assert mermaid_problems("flowchart BT;\nA-->B") == []


@pytest.mark.parametrize(
    ("code", "edge"),
    [
        # Faux refus de la re-relecture 3, admis désormais.
        ("A -- pré-requis --> B", '-->|"pré-requis"|'),
        ("A -. v1.2 .-> B", '-.->|"v1.2"|'),
        ("A ----> B", "---->"),
        ("A --> B %% note", "-->"),
        ("A <--> B", "<-->"),
        # Variantes.
        ("A <-.-> B", "<-.->"),
        ("A <==> B", "<==>"),
        ("A -..-> B", "-..->"),
        ("A ====> B", "====>"),
        ("A ---- B", "----"),
        ("A -- x = y + 1 ---> B", '--->|"x = y + 1"|'),
        ('A -- "a -- b" --> B', '-->|"a -- b"|'),
        ('A -- "x --> y ; z" --> B', '-->|"x --#gt; y ; z"|'),
        ("A == mène à === B", '===|"mène à"|'),
        ("A <-->|double| B", '<-->|"double"|'),
    ],
)
def test_more_mermaid_edge_forms_are_accepted(code: str, edge: str) -> None:
    out = normalize_mermaid(f"flowchart LR\n{code}")
    assert out == f'flowchart LR\n  n1["A"] {edge} n2["B"]'
    assert normalize_mermaid(out) == out


@pytest.mark.parametrize("label", ['""', '"<br>"', '"   "', '" <br/> "'])
def test_an_empty_label_falls_back_to_the_source_identifier(label: str) -> None:
    code = f"flowchart TD\nEtape[{label}] --> B\nsubgraph S[{label}]\nC\nend"
    assert normalize_mermaid(code) == (
        'flowchart TD\n  n1["Etape"] --> n2["B"]\n  subgraph n3["S"]\n    n4["C"]\n  end'
    )
