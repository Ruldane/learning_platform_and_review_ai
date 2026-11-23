from app.agents.tools.expert_debate_port import EXPERT_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="expert_debates",
    actions=(
        McpAction(
            "GET /expert-debates",
            1,
            "expert_debates_list_recent",
            "Liste les débats du compte.",
            untrusted=("[].question",),
        ),
        McpAction(
            "GET /expert-debates/{debate_id}",
            1,
            "expert_debates_read_thread",
            "Lit les prises de parole, leurs sources et le jugement de l’utilisatrice.",
            untrusted=(
                "question",
                "judgment",
                "speeches[].text",
                "speeches[].citations[].title",
                "speeches[].citations[].url",
            ),
        ),
        McpAction(
            "POST /expert-debates",
            2,
            "expert_debates_start_debate",
            "Pose une question au débat et lance le parcours.",
            launches="expert_debate",
            untrusted=("question",),
        ),
        McpAction(
            "PUT /expert-debates/{debate_id}/judgment",
            3,
            "expert_debates_judge_debate",
            "Enregistre le jugement personnel sur le débat. Demande à confirmer.",
            untrusted=(
                "question",
                "judgment",
                "speeches[].text",
                "speeches[].citations[].title",
                "speeches[].citations[].url",
            ),
        ),
    ),
    graphs=(McpGraph(EXPERT_GRAPH, follow_only=True),),
)
