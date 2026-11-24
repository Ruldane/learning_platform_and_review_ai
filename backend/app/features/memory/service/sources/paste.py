from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    decode_text,
    read_stored,
)


class PasteSource:
    """Pasted text, stored as a `.txt` file (D66); title: the one entered, otherwise
    "Pasted text from DD/MM/YYYY", already set as the document name on creation."""

    kind: DocumentSourceKind = "paste"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = decode_text(await read_stored(source, tools))
        return Extracted(title=source.name, text=text)
