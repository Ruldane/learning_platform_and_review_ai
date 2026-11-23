from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="podcast",
    actions=(
        McpAction(
            "GET /podcast/today",
            1,
            "podcast_read_today",
            "Lit la transcription et les questions de l’épisode du jour.",
            untrusted=("title", "lines[].text", "questions[].question", "questions[].choices[]"),
        ),
        McpAction(
            "POST /podcast/today",
            3,
            "podcast_prepare_today",
            "Demande la synthèse de l’épisode du jour avec le chapitre prévu, à confirmer.",
            side_effects="external",
            launches="podcast",
        ),
        McpAction(
            "POST /podcast/{episode_id}/quiz",
            2,
            "podcast_grade_quiz",
            "Vérifie les trois choix soumis et donne les explications.",
            untrusted=("corrections[].explanation",),
        ),
        McpAction(
            "GET /podcast/{episode_id}/audio",
            1,
            "podcast_get_episode_audio",
            "Lit les métadonnées de l’épisode audio et donne son lien local.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph("podcast", follow_only=True, summary="Écrit et met en voix l’épisode du matin."),
    ),
)
