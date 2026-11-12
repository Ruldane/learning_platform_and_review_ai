"""Rendu de nos gabarits HTML en PDF A4 par Gotenberg 8 (`POST /forms/chromium/convert/html`,
D89) : leçons et programme. `index.html`, le pied de page et les ressources (nos fichiers figés)
partent dans le même formulaire ; Chromium les ouvre depuis un dossier de `/tmp` (le seul
`file:` que sa liste de refus laisse passer, D72).

Mêmes règles d'erreur que le rendu d'une URL (`post_for_pdf`) : `RenderFailed`, corps borné à
`RENDER_MAX_BYTES`, ni le HTML ni la réponse dans un message ou un journal."""

import httpx

from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, HtmlDocument
from app.providers.pdf.gotenberg import FormFiles, post_for_pdf

_ROUTE = "/forms/chromium/convert/html"
# A4 en pouces (unité par défaut de Gotenberg), marges de 0,6 pouce (le pied de page y tient).
PAPER_WIDTH = "8.27"
PAPER_HEIGHT = "11.7"
MARGIN = "0.6"
_TYPES = {"css": "text/css", "js": "text/javascript"}


def _page_fields(document: HtmlDocument) -> FormFiles:
    fields: FormFiles = [
        ("paperWidth", (None, PAPER_WIDTH)),
        ("paperHeight", (None, PAPER_HEIGHT)),
        ("marginTop", (None, MARGIN)),
        ("marginBottom", (None, MARGIN)),
        ("marginLeft", (None, MARGIN)),
        ("marginRight", (None, MARGIN)),
        ("printBackground", (None, "true")),
    ]
    if document.wait_for_expression is not None:
        fields.append(("waitForExpression", (None, document.wait_for_expression)))
    return fields


def html_form(document: HtmlDocument) -> FormFiles:
    """Champs du formulaire : fichiers sous `files` (nom de fichier = nom servi), puis réglages
    de la page."""
    files: FormFiles = [("files", ("index.html", document.index_html.encode(), "text/html"))]
    if document.footer_html is not None:
        files.append(("files", ("footer.html", document.footer_html.encode(), "text/html")))
    for name in sorted(document.assets):
        kind = _TYPES[name.rsplit(".", 1)[1]]
        files.append(("files", (name, document.assets[name], kind)))
    return files + _page_fields(document)


class GotenbergHtmlRenderer:
    """`HtmlPdfRenderer` sur un client dédié (`bootstrap.publishing_providers`)."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._endpoint = base_url.rstrip("/") + _ROUTE

    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        form = html_form(document)
        return await post_for_pdf(self._http, self._endpoint, form, timeout_s=timeout_s)
