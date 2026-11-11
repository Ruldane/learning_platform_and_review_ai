from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    decode_text,
    read_stored,
    stem,
)


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None


class MarkdownSource:
    """Texte Markdown brut ; titre : premier titre `# `, sinon nom sans extension."""

    kind: DocumentSourceKind = "markdown"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = decode_text(await read_stored(source, tools))
        return Extracted(title=_first_h1(text) or stem(source.name), text=text)
