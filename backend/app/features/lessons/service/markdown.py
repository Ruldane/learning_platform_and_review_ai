"""Markdown d'une leçon en HTML sûr (SPEC 3.5, 17.4, D89). La leçon est écrite par un agent qui
a lu des pages web : son texte est **non fiable**.

1. `markdown-it-py` en `commonmark` avec tables ; le **HTML brut n'est jamais rendu** : le
   parseur le reconnaît (balise, commentaire, bloc) pour le **retirer** (règles de rendu vides),
   ce qui est plus strict que l'échapper (D89) ; une image devient son texte de remplacement
   (rien n'est chargé).
2. Bloc ```` ```mermaid ```` : analysé par la grammaire stricte du Scribe puis **réémis**
   (`normalize_mermaid`, D85 §11f) ; seule la version régénérée entre dans `<pre class="mermaid">`,
   au texte échappé. Refusé : un encadré « schéma indisponible », jamais le code d'origine.
3. Sections de niveau 2 : titre ancré (`s<n>-<slug>`), sommaire, encadrés pour « L'essentiel en
   5 lignes » et « Erreurs fréquentes ».
4. `nh3.clean` en liste blanche : balises `ALLOWED_TAGS`, attributs `href` / `id` / `class`
   (classes connues seulement), liens `http` et `https` (relatifs refusés), `rel="noopener
   noreferrer"`. Ni script, ni style, ni gestionnaire d'événement, ni image, ni iframe."""

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
# Au-delà, le texte est coupé : une leçon fait 1 200 à 2 500 mots (SPEC 3.5).
MAX_MARKDOWN_CHARS = 200_000
MERMAID_BLOCK = '<pre class="mermaid">'
UNAVAILABLE = '<aside class="diagram-unavailable"><p>Schéma indisponible.</p></aside>\n'


@dataclass(frozen=True)
class RenderedMarkdown:
    html: str
    toc: list[tuple[str, str]]  # (ancre, titre de section)
    diagrams: int  # blocs Mermaid acceptés (rendus en SVG si les scripts tournent)


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


# `html: True` pour le parseur seulement : le HTML brut devient des jetons `html_inline` /
# `html_block`, rendus vides (jamais copiés ni échappés).
_MD = MarkdownIt("commonmark", {"html": True}).enable("table")
_MD.add_render_rule("fence", _fence)
_MD.add_render_rule("image", _image)
_MD.add_render_rule("html_inline", _dropped)
_MD.add_render_rule("html_block", _dropped)


def _plain(inline: Token) -> str:
    """Texte d'un titre, sans mise en forme."""
    parts = [t.content for t in inline.children or [] if t.type in ("text", "code_inline")]
    return " ".join("".join(parts).split())


def _folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _folded(title)).strip("-")
    return slug[:48].strip("-") or "section"


def _section_class(title: str) -> str:
    folded = _folded(title)
    if "essentiel" in folded:
        return "lesson-section callout callout-key"
    if "erreurs frequentes" in folded:
        return "lesson-section callout callout-warning"
    return "lesson-section"


def _chunks(tokens: list[Token]) -> list[list[Token]]:
    """Découpe aux titres h2 de premier niveau (pas ceux d'une citation ou d'une liste)."""
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


def markdown_to_html(markdown: str) -> RenderedMarkdown:
    env: dict[str, Any] = {"diagrams": 0}
    tokens = _MD.parse(markdown[:MAX_MARKDOWN_CHARS], env)
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
