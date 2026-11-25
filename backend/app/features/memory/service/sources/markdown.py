from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.obsidian import split_header
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
    """Raw Markdown text; title: first `# ` heading, otherwise name without extension."""

    kind: DocumentSourceKind = "markdown"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = decode_text(await read_stored(source, tools))
        title = None
        if source.sync_metadata is not None:
            _, text = split_header(text)
            title = source.sync_metadata.get("title")
        return Extracted(title=title or _first_h1(text) or stem(source.name), text=text)
