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
        McpAction(
            "POST /linkedin-drafts",
            2,
            "linkedin_drafts_start_draft",
            "Prépare un brouillon de profil LinkedIn.",
            launches="linkedin_draft",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
        McpAction(
            "PUT /linkedin-drafts/{draft_id}",
            2,
            "linkedin_drafts_update_draft",
            "Retouche les textes du brouillon de profil LinkedIn.",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
