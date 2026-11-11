from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    required_url,
)


class YoutubeSource:
    """Transcription (repli : titre et description) ; titre : celui de la vidéo, sinon
    « Vidéo YouTube <id> »."""

    kind: DocumentSourceKind = "youtube"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        transcript = await tools.youtube.transcript(required_url(source))
        title = (transcript.title or "").strip() or f"Vidéo YouTube {transcript.video_id}"
        return Extracted(title=title, text=transcript.text)
