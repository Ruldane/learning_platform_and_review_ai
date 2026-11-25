from urllib.parse import urlsplit

from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    required_url,
)


class UrlSource:
    """Page read by the safe reader (SSRF guard, 15 s, 20 MB); title: the page's, otherwise
    the host; language: the one from the page metadata."""

    kind: DocumentSourceKind = "url"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        url = required_url(source)
        page = await tools.web.read(url)
        title = (page.title or "").strip() or (urlsplit(url).hostname or source.name)
        return Extracted(title=title, text=page.text, lang=page.lang)
