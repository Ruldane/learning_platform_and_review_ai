"""Leçon en PDF A4 (SPEC 3.5, 17.4, D89) : gabarit unique `lesson/lesson.html.j2` (échappement
automatique), sommaire, encadrés, schémas Mermaid en SVG, numéros de page, thème clair.

Les seuls scripts de la page sont nos fichiers figés (`mermaid.min.js` à empreinte vérifiée,
`render.js`), et seulement si la leçon a au moins un schéma accepté ; Gotenberg attend alors
`window.__lessonReady === true`. Si ce rendu échoue (`RenderFailed`), second essai sans aucun
script : les schémas s'affichent en code (la version réémise par le back, jamais l'originale).
Une politique de sécurité du contenu (`<meta>`) interdit en plus toute requête et toute image."""

import logging
import re

from markupsafe import Markup

from app.features.lessons.service.markdown import MERMAID_BLOCK, markdown_to_html
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer, RenderFailed
from app.templates import render_template
from app.templates.assets import asset, template_file

logger = logging.getLogger(__name__)

LESSON_READY = "window.__lessonReady === true"
# Rien hors de nos fichiers joints : ni requête, ni image, ni cadre, ni formulaire. Le style
# en ligne reste permis (Mermaid en met dans le SVG qu'il produit).
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
    """Page de la leçon ; `body` est du HTML déjà nettoyé (`markdown_to_html`)."""
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
        body=Markup(body),  # noqa: S704  (nettoyé par nh3, liste blanche)
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
    content = markdown_to_html(markdown, drop_title=True)  # le titre est déjà en couverture

    def page(scripts: bool) -> HtmlDocument:
        return lesson_document(
            title=title, body=content.html, toc=content.toc, language=language, scripts=scripts
        )

    if not content.diagrams:
        return await renderer.html_to_pdf(page(scripts=False))
    try:
        return await renderer.html_to_pdf(page(scripts=True))
    except RenderFailed:
        # Nombre seulement : ni titre ni contenu dans un journal (17.2).
        logger.info("Leçon : schémas non rendus (%d), second essai sans script", content.diagrams)
    return await renderer.html_to_pdf(page(scripts=False))
