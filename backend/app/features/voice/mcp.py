from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="voice",
    actions=(
        McpAction(
            "POST /voice/transcriptions",
            1,
            "voice_open_recording",
            "Tells where to record and transcribe an answer from a microphone.",
            manual_url="/etudier",
        ),
        McpAction(
            "POST /voice/speech",
            1,
            "voice_open_playback",
            "Tells where to listen to an answer with the Tremplin player.",
            manual_url="/etudier",
        ),
    ),
)
