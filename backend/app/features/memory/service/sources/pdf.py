from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    read_stored,
    stem,
)


class PdfSource:
    """Page text (pdfplumber, capped by the provider); title: name without extension."""

    kind: DocumentSourceKind = "pdf"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = await tools.pdf.extract_text(await read_stored(source, tools))
        return Extracted(title=stem(source.name), text=text)
