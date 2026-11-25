from app.db.models.memory import DocumentSourceKind
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    required_url,
)


class YoutubeSource:
    """Transcript (fallback: title and description); title: the video's, otherwise
    "YouTube video <id>"."""

    kind: DocumentSourceKind = "youtube"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        transcript = await tools.youtube.transcript(required_url(source))
        title = (transcript.title or "").strip() or f"YouTube video {transcript.video_id}"
        return Extracted(title=title, text=transcript.text)
