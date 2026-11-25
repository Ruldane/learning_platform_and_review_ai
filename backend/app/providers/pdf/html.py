"""Rendering of our HTML templates to PDF through Gotenberg 8 (`POST /forms/chromium/convert/html`,
D89): lessons and program in A4, CVs at the size of their original page, zero margins (D119).
`index.html`, the footer and the resources (our frozen files, the free fonts) go in the same form;
Chromium opens them from a folder under `/tmp` (the only `file:` its deny list lets through, D72).

Same error rules as rendering a URL (`post_for_pdf`): `RenderFailed`, body bounded to
`RENDER_MAX_BYTES`, neither the HTML nor the response in a message or a log."""

import httpx

from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, HtmlDocument, PageSetup
from app.providers.pdf.gotenberg import FormFiles, post_for_pdf

_ROUTE = "/forms/chromium/convert/html"
# A4 in inches (Gotenberg's default unit), margins of 0.6 inch (the footer fits in them).
PAPER_WIDTH = "8.27"
PAPER_HEIGHT = "11.7"
MARGIN = "0.6"
DEFAULT_PAGE = PageSetup(PAPER_WIDTH, PAPER_HEIGHT, (MARGIN, MARGIN, MARGIN, MARGIN))
_TYPES = {"css": "text/css", "js": "text/javascript", "woff2": "font/woff2", "ttf": "font/ttf"}


def _page_fields(document: HtmlDocument) -> FormFiles:
    page = document.page or DEFAULT_PAGE
    top, right, bottom, left = page.margins_in
    fields: FormFiles = [
        ("paperWidth", (None, page.width_in)),
        ("paperHeight", (None, page.height_in)),
        ("marginTop", (None, top)),
        ("marginBottom", (None, bottom)),
        ("marginLeft", (None, left)),
        ("marginRight", (None, right)),
        ("printBackground", (None, "true")),
    ]
    if document.wait_for_expression is not None:
        fields.append(("waitForExpression", (None, document.wait_for_expression)))
    return fields


def html_form(document: HtmlDocument) -> FormFiles:
    """Form fields: files under `files` (file name = served name), then the page settings."""
    files: FormFiles = [("files", ("index.html", document.index_html.encode(), "text/html"))]
    if document.footer_html is not None:
        files.append(("files", ("footer.html", document.footer_html.encode(), "text/html")))
    for name in sorted(document.assets):
        kind = _TYPES[name.rsplit(".", 1)[1]]
        files.append(("files", (name, document.assets[name], kind)))
    return files + _page_fields(document)


class GotenbergHtmlRenderer:
    """`HtmlPdfRenderer`, on a dedicated client (`bootstrap.publishing_providers`)."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._endpoint = base_url.rstrip("/") + _ROUTE

    async def html_to_pdf(
        self, document: HtmlDocument, *, timeout_s: float = HTML_RENDER_TIMEOUT_S
    ) -> bytes:
        form = html_form(document)
        return await post_for_pdf(self._http, self._endpoint, form, timeout_s=timeout_s)
