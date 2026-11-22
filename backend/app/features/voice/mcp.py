from app.mcp.base import FeatureMcp

MCP = FeatureMcp(
    feature="voice",
    excluded={
        "POST /voice/transcriptions": "Enregistrement envoyé depuis l’interface.",
        "POST /voice/speech": "Lecture audio demandée depuis l’interface par l’utilisatrice.",
    },
)
