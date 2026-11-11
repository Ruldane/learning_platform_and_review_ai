from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    decode_text,
    read_stored,
    stem,
)


class TextSource:
    """Fichier texte ; titre : nom sans extension."""

    kind: DocumentSourceKind = "text"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = decode_text(await read_stored(source, tools))
        return Extracted(title=stem(source.name), text=text)
