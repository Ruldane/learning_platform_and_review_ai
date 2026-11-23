from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="voice",
    actions=(
        McpAction(
            "POST /voice/transcriptions",
            1,
            "voice_open_recording",
            "Indique où enregistrer et transcrire une réponse depuis un microphone.",
            manual_url="/etudier",
        ),
        McpAction(
            "POST /voice/speech",
            1,
            "voice_open_playback",
            "Indique où écouter une réponse avec le lecteur de Tremplin.",
            manual_url="/etudier",
        ),
    ),
)
