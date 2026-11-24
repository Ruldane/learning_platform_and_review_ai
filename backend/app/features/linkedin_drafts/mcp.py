from app.agents.tools.linkedin_port import GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="linkedin_drafts",
    actions=(
        McpAction(
            "GET /linkedin-drafts/latest",
            1,
            "linkedin_drafts_read_latest",
            "Reads the profile proposal and the claims to fix.",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
        McpAction(
            "POST /linkedin-drafts",
            2,
            "linkedin_drafts_start_draft",
            "Prepares a LinkedIn profile draft.",
            launches="linkedin_draft",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
        McpAction(
            "PUT /linkedin-drafts/{draft_id}",
            2,
            "linkedin_drafts_update_draft",
            "Edits the texts of the LinkedIn profile draft.",
            untrusted=("text.headline", "text.about", "text.skills", "claims[].term"),
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
