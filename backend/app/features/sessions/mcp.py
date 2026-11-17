"""Déclaration MCP de `sessions` : suivre une session d'agents et lui répondre. Lancer un parcours
se fait par l'outil de son graphe (`McpGraph`), jamais par `POST /sessions` brut."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="sessions",
    actions=(
        McpAction(
            "GET /sessions",
            1,
            "sessions_list_sessions",
            "Les sessions d'agents, filtrables par parcours et par statut.",
        ),
        McpAction(
            "GET /sessions/{session_id}",
            1,
            "sessions_get_session",
            "État d'une session : statut, question en attente, erreur, consommation.",
        ),
        McpAction(
            "POST /sessions/{session_id}/resume",
            3,
            "sessions_answer_session",
            "Répond à la question en attente d'une session. C'est la décision de January "
            "(valider un programme, accepter un replan, confirmer une fiche) : demande à "
            "confirmer.",
        ),
        McpAction(
            "POST /sessions/{session_id}/message",
            2,
            "sessions_post_message",
            "Envoie un message ou une commande à une session en cours.",
        ),
        McpAction(
            "POST /sessions/{session_id}/pause",
            2,
            "sessions_pause_session",
            "Met une session en pause.",
        ),
        McpAction(
            "POST /sessions/{session_id}/cancel",
            2,
            "sessions_cancel_session",
            "Annule une session en cours.",
        ),
    ),
    excluded={
        "POST /sessions": (
            "Lancement brut d'un parcours par son nom : remplacé par un outil par graphe "
            "(`McpGraph`), dont l'entrée est validée par le modèle d'entrée du parcours."
        ),
        "WS /sessions/{session_id}/stream": (
            "WebSocket de diffusion des événements : le MCP suit une session par "
            "`sessions_get_session`, il n'ouvre pas de flux."
        ),
        "graph:demo_debate": (
            "Parcours de démo interne du débat (phase 3), aucune action de l'utilisatrice ne le "
            "lance : il consommerait des appels au modèle sans rien produire."
        ),
    },
)
