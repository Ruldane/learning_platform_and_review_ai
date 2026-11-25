"""A lesson's Markdown as safe HTML (SPEC 3.5, 17.4, D89). The lesson is written by an agent
that read web pages: its text is **untrusted**.

1. `markdown-it-py` in `commonmark` mode with tables; **raw HTML is never rendered**: the parser
   recognizes it in order to neutralize it. An inline tag (`html_inline`) is **removed** (D89);
   an HTML block (`html_block`) becomes **escaped text** inside a `<p>` (D97): a `<pre>` or
   `<script>` never closed, running to the end of the document, no longer swallows the rest of
   the lesson. The Verifier rejects raw HTML outside code anyway. An image becomes its
   alternative text (nothing is loaded).
2. ```` ```mermaid ```` block: parsed by the Scribe's strict grammar then **re-emitted**
   (`normalize_mermaid`, D85 §11f); only the regenerated version goes into
   `<pre class="mermaid">`, as escaped text. Rejected: a "diagram unavailable" box, never the
   original code.
3. Level-2 sections have anchored headings (`s<n>-<slug>`) and contents entries. Key points
   and common mistakes are highlighted, including in saved French lessons.
4. Allow-list `nh3.clean`: `ALLOWED_TAGS` tags, `href` / `id` / `class` attributes (known
   classes only), `http` and `https` links (relative ones rejected), `rel="noopener
   noreferrer"`. No script, style, event handler, image or iframe."""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import nh3
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markdown_it.token import Token

from app.agents.nodes.mermaid_rules import normalize_mermaid
from app.core.lesson_structure import COMMON_MISTAKES, KEY_POINTS, reading_section

ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "code", "pre", "blockquote",
    "a", "table", "thead", "tbody", "tr", "th", "td", "hr", "br", "div", "section", "aside", "span",
}  # fmt: skip
_CLASSES = {
    "pre": {"mermaid", "mermaid-source"},
    "section": {"lesson-section", "callout", "callout-key", "callout-warning"},
    "aside": {"diagram-unavailable"},
    "span": {"image-omitted"},
}
_ATTRIBUTES = {"a": {"href"}, "h2": {"id"}}
# Beyond this, the text is cut: a lesson is 1,200 to 2,500 words long (SPEC 3.5).
MAX_MARKDOWN_CHARS = 200_000
MERMAID_BLOCK = '<pre class="mermaid">'
UNAVAILABLE = '<aside class="diagram-unavailable"><p>Diagram unavailable.</p></aside>\n'


@dataclass(frozen=True)
class RenderedMarkdown:
    html: str
    toc: list[tuple[str, str]]  # (anchor, section title)
    diagrams: int  # accepted Mermaid blocks (rendered as SVG if scripts run)


def _fence(_renderer: Any, tokens: Sequence[Token], idx: int, _opts: Any, env: Any) -> str:
    token = tokens[idx]
    info = token.info.strip().split(maxsplit=1)
    if not info or info[0].lower() != "mermaid":
        return f"<pre><code>{escapeHtml(token.content)}</code></pre>\n"
    try:
        code = normalize_mermaid(token.content)
    except ValueError:
        return UNAVAILABLE
    env["diagrams"] = env.get("diagrams", 0) + 1
    return f"{MERMAID_BLOCK}{escapeHtml(code)}</pre>\n"


def _image(renderer: Any, tokens: Sequence[Token], idx: int, opts: Any, env: Any) -> str:
    alt = renderer.renderInlineAsText(tokens[idx].children or [], opts, env)
    return f'<span class="image-omitted">[{escapeHtml(alt)}]</span>'


def _dropped(_renderer: Any, _tokens: Sequence[Token], _idx: int, _opts: Any, _env: Any) -> str:
    return ""


def _escaped_block(_renderer: Any, tokens: Sequence[Token], idx: int, _opts: Any, _env: Any) -> str:
    return f"<p>{escapeHtml(tokens[idx].content.strip())}</p>\n"


# `html: True` for the parser only: raw HTML becomes `html_inline` tokens (removed) and
# `html_block` tokens (escaped text), never copied as is.
_MD = MarkdownIt("commonmark", {"html": True}).enable("table")
_MD.add_render_rule("fence", _fence)
_MD.add_render_rule("image", _image)
_MD.add_render_rule("html_inline", _dropped)
_MD.add_render_rule("html_block", _escaped_block)


def _plain(inline: Token) -> str:
    """Text of a heading, without formatting."""
    parts = [t.content for t in inline.children or [] if t.type in ("text", "code_inline")]
    return " ".join("".join(parts).split())


def _folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _folded(title)).strip("-")
    return slug[:48].strip("-") or "section"


def _section_class(title: str) -> str:
    section = reading_section(title)
    folded = _folded(title)
    if section == KEY_POINTS or "essentiel" in folded:
        return "lesson-section callout callout-key"
    if section == COMMON_MISTAKES or "erreurs frequentes" in folded:
        return "lesson-section callout callout-warning"
    return "lesson-section"


def _chunks(tokens: list[Token]) -> list[list[Token]]:
    """Splits at top-level h2 headings (not those inside a quote or a list)."""
    chunks: list[list[Token]] = [[]]
    for token in tokens:
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            chunks.append([])
        chunks[-1].append(token)
    return [chunk for chunk in chunks if chunk]


def _clean(html: str) -> str:
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=_ATTRIBUTES,
        allowed_classes=_CLASSES,
        url_schemes={"http", "https"},
        url_relative="deny",
        link_rel="noopener noreferrer",
        strip_comments=True,
    )


def _without_title(tokens: list[Token]) -> list[Token]:
    """Without the first h1 before any section: the PDF already shows it on the cover."""
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and token.tag in ("h1", "h2"):
            return tokens[:index] + tokens[index + 3 :] if token.tag == "h1" else tokens
    return tokens


def markdown_to_html(markdown: str, *, drop_title: bool = False) -> RenderedMarkdown:
    """`drop_title`: removes the leading `# …` title (PDF only, D97); the application view
    reads the Markdown as is."""
    env: dict[str, Any] = {"diagrams": 0}
    tokens = _MD.parse(markdown[:MAX_MARKDOWN_CHARS], env)
    if drop_title:
        tokens = _without_title(tokens)
    toc: list[tuple[str, str]] = []
    parts: list[str] = []
    for chunk in _chunks(tokens):
        if chunk[0].type != "heading_open" or chunk[0].tag != "h2":
            parts.append(_MD.renderer.render(chunk, _MD.options, env))
            continue
        title = _plain(chunk[1])
        anchor = f"s{len(toc) + 1}-{_slug(title)}"
        chunk[0].attrSet("id", anchor)
        toc.append((anchor, title))
        body = _MD.renderer.render(chunk, _MD.options, env)
        parts.append(f'<section class="{_section_class(title)}">\n{body}</section>\n')
    return RenderedMarkdown(_clean("".join(parts)), toc, int(env["diagrams"]))
