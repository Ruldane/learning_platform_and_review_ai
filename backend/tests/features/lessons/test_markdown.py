"""Markdown d'une leçon en HTML sûr (SPEC 3.5, 17.4, D89) : HTML brut échappé, liste blanche
`nh3`, liens `http(s)` seulement, aucune image, Mermaid réémis ou remplacé."""

import re

import pytest

from app.features.lessons.service.markdown import ALLOWED_TAGS, markdown_to_html

FLOW = "```mermaid\nflowchart TD\nA[Début] --> B[Fin]\n```"


def _tags(html: str) -> set[str]:
    return {tag.lower() for tag in re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)", html)}


def test_markdown_escapes_raw_html() -> None:
    out = markdown_to_html("Texte <script>alert(1)</script> <img src=x onerror=alert(1)>")
    assert "<script" not in out.html and "onerror" not in out.html and "<img" not in out.html
    assert out.html.startswith("<p>Texte")  # le HTML brut est retiré, le texte reste


def test_html_in_code_stays_visible_as_text() -> None:
    out = markdown_to_html("Écrire `<script>` ou :\n\n```html\n<img onerror=x>\n```")
    assert "<code>&lt;script&gt;</code>" in out.html
    assert "&lt;img onerror=x&gt;" in out.html and "<img" not in out.html


def test_raw_html_blocks_are_escaped() -> None:
    out = markdown_to_html(
        '<iframe src="https://evil.example"></iframe>\n\n<div onclick="x()">a</div>\n\n'
        "<style>body{display:none}</style>"
    )
    assert _tags(out.html) <= {"p"}
    assert "<iframe" not in out.html and "<style" not in out.html
    assert "&lt;iframe" in out.html  # bloc rendu en texte inerte, pas jeté


def test_unclosed_html_block_keeps_the_rest_as_text() -> None:
    """Revue finale de la phase 4, I2 : `<pre>` jamais refermé n'avale plus la suite."""
    out = markdown_to_html("## Objectifs\n- a\n<pre>\nx\n## Explication\nLong texte important.\n")
    assert "Explication" in out.html and "important" in out.html
    assert "<pre" not in out.html and _tags(out.html) <= ALLOWED_TAGS


def test_inline_html_is_still_dropped() -> None:
    out = markdown_to_html("Texte <img src=x onerror=alert(1)> fin")
    assert "onerror" not in out.html and "img" not in out.html


def test_pdf_body_drops_the_leading_title_only_when_asked() -> None:
    markdown = "# Titre de la leçon\n\n## Objectifs\n\n# Autre titre\n"
    assert out_h1(markdown_to_html(markdown).html) == ["Titre de la leçon", "Autre titre"]
    assert out_h1(markdown_to_html(markdown, drop_title=True).html) == ["Autre titre"]


def out_h1(html: str) -> list[str]:
    return re.findall(r"<h1>(.*?)</h1>", html)


@pytest.mark.parametrize(
    "link",
    [
        "[x](javascript:alert(1))",
        "[x](JaVaScRiPt:alert(1))",
        "[x](data:text/html;base64,PHNjcmlwdD4=)",
        "[x](vbscript:msgbox)",
        "[x](file:///etc/passwd)",
        "[x](/api/v1/programs)",
        "[x](../../secret)",
        "<javascript:alert(1)>",
    ],
)
def test_javascript_links_are_dropped(link: str) -> None:
    out = markdown_to_html(link)
    assert "href" not in out.html
    assert "javascript:" not in out.html.lower() or "href" not in out.html


def test_http_links_keep_href_and_rel() -> None:
    out = markdown_to_html("[doc](https://docs.python.org/3/)")
    assert '<a href="https://docs.python.org/3/" rel="noopener noreferrer">doc</a>' in out.html


def test_images_are_never_loaded() -> None:
    out = markdown_to_html("![schéma <b>piégé</b>](https://evil.example/pixel.png)")
    assert "<img" not in out.html and "evil.example" not in out.html
    assert "schéma" in out.html


def test_mermaid_block_becomes_pre_mermaid() -> None:
    out = markdown_to_html(FLOW)
    assert out.diagrams == 1
    [code] = re.findall(r'<pre class="mermaid">(.*?)</pre>', out.html, re.S)
    assert code.startswith("flowchart TD\n")
    assert 'n1["Début"] --&gt; n2["Fin"]' in code.replace("&quot;", '"')


def test_mermaid_directives_are_removed() -> None:
    html = markdown_to_html('```mermaid\nflowchart TD\nA-->B\nclick A "x"\n```').html
    assert 'class="mermaid"' not in html
    assert "click" not in html and "diagram-unavailable" in html


@pytest.mark.parametrize(
    "code",
    [
        '%%{init: {"securityLevel": "loose"}}%%\nflowchart TD\nA-->B',
        "flowchart TD\nA-->B\nstyle A fill:#f00",
        "sequenceDiagram\nA->>B: hi",
        'flowchart TD\nA["</pre><script>alert(1)</script>"]-->B',
        "flowchart TD\nA-->B\nclick A call alert(1)",
    ],
)
def test_refused_mermaid_is_never_copied(code: str) -> None:
    html = markdown_to_html(f"```mermaid\n{code}\n```").html
    assert "<script" not in html and "init" not in html and "click" not in html
    if 'class="mermaid"' in html:  # accepté seulement s'il a été réémis
        assert "&lt;script&gt;" not in html or "#lt;" in html
    assert "alert(1)</" not in html


def test_mermaid_label_cannot_break_out_of_pre() -> None:
    out = markdown_to_html('```mermaid\nflowchart TD\nA["</pre><script>x</script>"]-->B\n```')
    assert "<script" not in out.html and "</pre><" not in out.html.replace("</pre>\n", "")


def test_toc_lists_h2_sections() -> None:
    out = markdown_to_html(
        "# Titre\n\n## Objectifs\n\ntexte\n\n## L'essentiel en *5* lignes\n\n- a\n\n"
        "### Détail\n\n## Erreurs fréquentes\n\n> ## pas une section\n"
    )
    assert [title for _, title in out.toc] == [
        "Objectifs",
        "L'essentiel en 5 lignes",
        "Erreurs fréquentes",
    ]
    anchors = [anchor for anchor, _ in out.toc]
    assert len(set(anchors)) == 3
    for anchor in anchors:
        assert re.fullmatch(r"s\d+-[a-z0-9-]+", anchor)
        assert f'id="{anchor}"' in out.html


def test_key_sections_become_callouts() -> None:
    out = markdown_to_html(
        "## Objectifs\n\nA\n\n## L’essentiel en 5 lignes\n\nB\n\n## Erreurs fréquentes\n\nC"
    )
    assert out.html.count('<section class="lesson-section">') == 1
    assert '<section class="lesson-section callout callout-key">' in out.html
    assert '<section class="lesson-section callout callout-warning">' in out.html


def test_output_tags_and_attributes_are_whitelisted() -> None:
    markdown = (
        "# T\n\n## S\n\n| a | b |\n|:--|--:|\n| 1 | 2 |\n\n```python\nprint('<x>')\n```\n\n"
        "    indenté\n\n> cité\n\n1. un\n2. deux\n\n---\n\n**gras** *it* `code`  \nfin\n\n" + FLOW
    )
    out = markdown_to_html(markdown)
    assert _tags(out.html) <= ALLOWED_TAGS
    attributes = set(re.findall(r"\s([a-zA-Z-]+)=", out.html))
    assert attributes <= {"href", "id", "class", "rel"}
    assert "style=" not in out.html


def test_allowed_tags_are_the_brief_list() -> None:
    assert {"script", "img", "iframe", "style", "svg", "object"}.isdisjoint(ALLOWED_TAGS)
