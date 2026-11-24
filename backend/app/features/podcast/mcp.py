from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="podcast",
    actions=(
        McpAction(
            "GET /podcast/today",
            1,
            "podcast_read_today",
            "Reads the transcript and the questions of today's episode.",
            untrusted=("title", "lines[].text", "questions[].question", "questions[].choices[]"),
        ),
        McpAction(
            "POST /podcast/today",
            3,
            "podcast_prepare_today",
            "Requests today's episode synthesis for the planned chapter; requires confirmation.",
            side_effects="external",
            launches="podcast",
        ),
        McpAction(
            "POST /podcast/{episode_id}/quiz",
            2,
            "podcast_grade_quiz",
            "Checks the three submitted choices and gives the explanations.",
            untrusted=("corrections[].explanation",),
        ),
        McpAction(
            "GET /podcast/{episode_id}/audio",
            1,
            "podcast_get_episode_audio",
            "Reads the audio episode's metadata and gives its local link.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph("podcast", follow_only=True, summary="Writes and voices the morning episode."),
    ),
)
