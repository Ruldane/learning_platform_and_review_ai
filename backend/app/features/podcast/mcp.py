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
            2,
            "podcast_prepare_today",
            "Prépare l’épisode du jour avec le chapitre prévu pour l’étude.",
            launches="podcast",
        ),
        McpAction(
            "POST /podcast/{episode_id}/quiz",
            2,
            "podcast_grade_quiz",
            "Vérifie les trois choix soumis et donne les explications.",
            untrusted=("corrections[].explanation",),
        ),
    ),
    graphs=(
        McpGraph("podcast", follow_only=True, summary="Écrit et met en voix l’épisode du matin."),
    ),
    excluded={"GET /podcast/{episode_id}/audio": "Flux binaire lu par le lecteur audio."},
)
