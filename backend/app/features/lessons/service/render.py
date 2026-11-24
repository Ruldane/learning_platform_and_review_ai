"""Lesson as an A4 PDF (SPEC 3.5, 17.4, D89): single `lesson/lesson.html.j2` template
(autoescaping), table of contents, callouts, Mermaid diagrams as SVG, page numbers, light theme.

The page's only scripts are our frozen files (`mermaid.min.js` with a verified hash,
`render.js`), and only if the lesson has at least one accepted diagram; Gotenberg then waits for
`window.__lessonReady === true`. If that rendering fails (`RenderFailed`), a second attempt runs
without any script: diagrams are shown as code (the version re-emitted by the back end, never the
original). A content security policy (`<meta>`) also forbids any request and any image."""

import logging
import re

from markupsafe import Markup

from app.features.lessons.service.markdown import MERMAID_BLOCK, markdown_to_html
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer, RenderFailed
from app.templates import render_template
from app.templates.assets import asset, template_file

logger = logging.getLogger(__name__)

LESSON_READY = "window.__lessonReady === true"
# Nothing outside our attached files: no request, image, frame or form. Inline style stays
# allowed (Mermaid puts some in the SVG it produces).
CSP_WITH_SCRIPTS = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src data:; font-src 'self'; base-uri 'none'; form-action 'none'"
)
CSP_WITHOUT_SCRIPTS = (
    "default-src 'none'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
)
_LABELS = {
    "fr": {"kicker": "Leçon", "toc": "Sommaire"},
    "en": {"kicker": "Lesson", "toc": "Contents"},
}
_LANGUAGE = re.compile(r"[a-z]{2}")


def _language(language: str) -> str:
    code = language.strip().lower()[:2]
    return code if _LANGUAGE.fullmatch(code) else "fr"


def lesson_document(
    *, title: str, body: str, toc: list[tuple[str, str]], language: str, scripts: bool
) -> HtmlDocument:
    """The lesson page; `body` is already sanitized HTML (`markdown_to_html`)."""
    code = _language(language)
    if not scripts:
        body = body.replace(MERMAID_BLOCK, '<pre class="mermaid-source">')
    index = render_template(
        "lesson/lesson.html.j2",
        language=code,
        csp=CSP_WITH_SCRIPTS if scripts else CSP_WITHOUT_SCRIPTS,
        title=title,
        labels=_LABELS.get(code, _LABELS["fr"]),
        toc=toc,
        body=Markup(body),  # noqa: S704  (sanitized by nh3, allow-list)
        scripts=scripts,
    )
    assets = {"lesson.css": template_file("lesson/lesson.css").encode()}
    if scripts:
        assets |= {"mermaid.min.js": asset("mermaid.min.js"), "render.js": asset("render.js")}
    return HtmlDocument(
        index_html=index,
        assets=assets,
        footer_html=template_file("lesson/footer.html"),
        wait_for_expression=LESSON_READY if scripts else None,
    )


async def render_lesson_pdf(
    renderer: HtmlPdfRenderer, *, title: str, markdown: str, language: str
) -> bytes:
    content = markdown_to_html(markdown, drop_title=True)  # the title is already on the cover

    def page(scripts: bool) -> HtmlDocument:
        return lesson_document(
            title=title, body=content.html, toc=content.toc, language=language, scripts=scripts
        )

    if not content.diagrams:
        return await renderer.html_to_pdf(page(scripts=False))
    try:
        return await renderer.html_to_pdf(page(scripts=True))
    except RenderFailed:
        # Count only: no title or content in a log (17.2).
        logger.info(
            "Lesson: diagrams not rendered (%d), second attempt without script", content.diagrams
        )
    return await renderer.html_to_pdf(page(scripts=False))
