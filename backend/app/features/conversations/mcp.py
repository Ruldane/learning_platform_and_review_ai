from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="conversations",
    actions=(
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
    ),
    graphs=(McpGraph(CONVERSATION_GRAPH, follow_only=True),),
)
