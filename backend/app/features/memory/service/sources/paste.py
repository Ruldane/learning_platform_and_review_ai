from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    decode_text,
    read_stored,
)


class PasteSource:
    """Texte collé, enregistré en `.txt` comme un fichier (D66) ; titre : celui saisi, sinon
    « Texte collé du JJ/MM/AAAA », déjà posé comme nom du document à sa création."""

    kind: DocumentSourceKind = "paste"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        text = decode_text(await read_stored(source, tools))
        return Extracted(title=source.name, text=text)
