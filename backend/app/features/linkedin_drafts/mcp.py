from app.agents.tools.linkedin_port import GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="linkedin_drafts",
    actions=(
        McpAction(
            "GET /linkedin-drafts/latest",
            1,
            "linkedin_drafts_read_latest",
            "Lit la proposition de profil et les affirmations à corriger.",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
    ),
    excluded={
        "POST /linkedin-drafts": "La rédaction est lancée sur la page du profil LinkedIn.",
        "PUT /linkedin-drafts/{draft_id}": "La correction se fait dans l’interface.",
    },
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
