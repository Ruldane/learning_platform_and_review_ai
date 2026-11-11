from urllib.parse import urlsplit

from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    required_url,
)


class UrlSource:
    """Page lue par le lecteur sûr (garde SSRF, 15 s, 20 Mo) ; titre : celui de la page, sinon
    l'hôte ; langue : celle des métadonnées de la page."""

    kind: DocumentSourceKind = "url"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        url = required_url(source)
        page = await tools.web.read(url)
        title = (page.title or "").strip() or (urlsplit(url).hostname or source.name)
        return Extracted(title=title, text=page.text, lang=page.lang)
