"""Déclaration MCP de `sessions` : suivre une session d'agents et lui répondre. Lancer un parcours
se fait par l'outil de son graphe (`McpGraph`), jamais par `POST /sessions` brut."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="sessions",
    actions=(
        McpAction(
            "GET /sessions/play",
            1,
            "agents_play_list",
            "Liste les lancements jouables ouverts à ce jeton et le schéma de leurs arguments.",
        ),
        McpAction(
            "POST /sessions/play",
            2,
            "agents_play_start",
            "Lance un parcours avec le modèle du client, par son outil de lancement.",
        ),
        McpAction(
            "GET /sessions/{session_id}/play",
            1,
            "agents_play_brief",
            "Lit les messages, le rôle et le schéma de la réponse attendue.",
        ),
        McpAction(
            "POST /sessions/{session_id}/play",
            2,
            "agents_play_submit",
            "Rend une réponse du modèle à l'étape indiquée.",
        ),
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
    graphs=(McpGraph("demo_debate", play_only=True),),
    excluded={
        "POST /sessions": (
            "Lancement brut d'un parcours par son nom : remplacé par un outil par graphe "
            "(`McpGraph`), dont l'entrée est validée par le modèle d'entrée du parcours."
        ),
        "WS /sessions/{session_id}/stream": (
            "WebSocket de diffusion des événements : le MCP suit une session par "
            "`sessions_get_session`, il n'ouvre pas de flux."
        ),
    },
)
