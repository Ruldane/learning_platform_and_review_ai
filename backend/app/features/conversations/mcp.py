from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_CHAT = "/conversations/{scope}"
_THREAD = _CHAT + "/{conversation_id}"
_FEYNMAN_CONTENT = (
    "source.title",
    "source.path",
    "report.explanation",
    "report.follow_up",
    "report.clarification",
    "report.summary",
    "report.cards[].front",
    "report.cards[].back",
)

MCP = FeatureMcp(
    feature="conversations",
    actions=(
        McpAction(
            f"GET {_CHAT}",
            1,
            "conversations_list",
            "Liste les conversations du Cerveau ou du training, avec recherche par titre.",
            untrusted=("[].title",),
        ),
        McpAction(
            f"PATCH {_THREAD}",
            2,
            "conversations_rename",
            "Renomme une conversation du Cerveau ou du training.",
            untrusted=("title",),
        ),
        McpAction(
            f"DELETE {_THREAD}/messages",
            3,
            "conversations_clear",
            "Vide les échanges d’une conversation. À confirmer dans Tremplin.",
            side_effects="external",
        ),
        McpAction(
            f"DELETE {_THREAD}",
            3,
            "conversations_delete",
            "Efface définitivement une conversation et ses échanges. À confirmer dans Tremplin.",
            side_effects="external",
        ),
        McpAction(
            f"DELETE {_CHAT}",
            3,
            "conversations_wipe",
            "Efface tous les fils du Cerveau ou du training. À confirmer dans Tremplin.",
            side_effects="external",
        ),
        McpAction(
            "GET /lessons/{lesson_id}/conversation",
            1,
            "conversations_read_professor",
            "Lit le fil du Professeur d'une leçon publiée, s'il existe.",
            untrusted=(
                "turns[].question",
                "turns[].passage",
                "turns[].answer",
                "turns[].sources[].title",
                "turns[].sources[].excerpt",
            ),
        ),
        McpAction(
            "POST /lessons/{lesson_id}/conversation/messages",
            2,
            "conversations_ask_professor",
            "Pose une question au Professeur d'une leçon publiée et rend l'identifiant de session. "
            "Réutilise le même request_id (UUID) pour rejouer l'envoi du même message.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/classroom",
            1,
            "conversations_read_classroom",
            "Lit la classe virtuelle d'une leçon publiée avec les réponses des trois camarades.",
            untrusted=(
                "turns[].question",
                "turns[].passage",
                "turns[].answer",
                "turns[].classmates[].answer",
                "turns[].sources[].title",
                "turns[].sources[].excerpt",
            ),
        ),
        McpAction(
            "POST /lessons/{lesson_id}/classroom/messages",
            2,
            "conversations_ask_classroom",
            "Partage une explication avec les trois camarades d'une leçon publiée. "
            "Réutilise le même request_id (UUID) pour rejouer l'envoi du même message.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /lessons/{lesson_id}/explain",
            1,
            "conversations_latest_lesson_explanation",
            "Lit la dernière explication Feynman sur une leçon.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /lessons/{lesson_id}/explain",
            2,
            "conversations_explain_lesson",
            "Ouvre une explication Feynman sur une leçon.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/explain",
            1,
            "conversations_latest_file_explanation",
            "Lit la dernière explication Feynman sur un fichier de l’atelier.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/explain",
            2,
            "conversations_explain_file",
            "Ouvre une explication Feynman sur un fichier de l’atelier.",
            launches=CONVERSATION_GRAPH,
        ),
        McpAction(
            "GET /conversations/explain/{turn_id}",
            1,
            "conversations_read_explanation",
            "Lit le bilan d’une explication Feynman.",
            untrusted=_FEYNMAN_CONTENT,
        ),
        McpAction(
            "POST /conversations/explain/{turn_id}/accept",
            3,
            "conversations_accept_explanation",
            "Enregistre les acquis d’une explication Feynman. À confirmer dans Tremplin.",
        ),
    ),
    graphs=(McpGraph(CONVERSATION_GRAPH, follow_only=True),),
)
