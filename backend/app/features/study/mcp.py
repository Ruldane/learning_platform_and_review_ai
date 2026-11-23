"""Déclaration MCP de `study` : la session guidée avec le Tuteur."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_TRAINING = "/study-sessions/training"
_TRAINING_SESSION = f"{_TRAINING}/{{study_session_id}}"
_TURN_CONTENT = (
    "conversation.turns[].question",
    "conversation.turns[].answer",
    "conversation.turns[].sources[].title",
    "conversation.turns[].sources[].excerpt",
)

MCP = FeatureMcp(
    feature="study",
    actions=(
        McpAction(
            "POST /study-sessions",
            2,
            "study_start_session",
            "Ouvre une session guidée sur une leçon (ou le bloc du jour) et lance le Tuteur.",
            launches="study_session",
        ),
        McpAction(
            "GET /study-sessions/summary",
            1,
            "study_get_summary",
            "Série, minutes de la semaine, minuteur, session ouverte et bloc du jour.",
        ),
        McpAction(
            "GET /study-sessions/{study_session_id}",
            1,
            "study_get_session",
            "Une session guidée, avec son écran de fin.",
        ),
        McpAction(
            "PATCH /study-sessions/{study_session_id}",
            2,
            "study_update_session",
            "Termine (`finish`) ou abandonne (`cancel`) une session guidée.",
        ),
        McpAction(
            f"POST {_TRAINING}",
            2,
            "study_start_training",
            "Ouvre ou reprend un training. new_conversation crée un fil indépendant.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"GET {_TRAINING}/open",
            1,
            "study_open_training",
            "Lit la session training ouverte, si elle existe.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"GET {_TRAINING_SESSION}",
            1,
            "study_read_training",
            "Lit le training, ses échanges et ses sources.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"PATCH {_TRAINING_SESSION}/context",
            2,
            "study_update_training_context",
            "Change le mode ou les leçons sélectionnées d’un training.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"PATCH {_TRAINING_SESSION}",
            3,
            "study_update_training",
            "Termine ou abandonne une session training. À confirmer dans Tremplin.",
            untrusted=_TURN_CONTENT,
        ),
        McpAction(
            f"POST {_TRAINING_SESSION}/messages",
            2,
            "study_talk_training",
            "Parle au Tuteur dans le fil, même après le bilan. "
            "Réutilise le même identifiant de demande pour rejouer un envoi.",
            launches="conversation",
        ),
    ),
    graphs=(
        McpGraph(
            "study_session",
            follow_only=True,
            summary="Le Tuteur conduit une session guidée (`study_session_id`).",
        ),
    ),
)
