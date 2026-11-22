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
    ),
    graphs=(McpGraph(EXPERT_GRAPH, follow_only=True),),
    excluded={
        "POST /expert-debates": "Question posée dans l’interface, puis recherche et modèles.",
        "PUT /expert-debates/{debate_id}/judgment": "Jugement personnel de l’utilisatrice.",
    },
)
