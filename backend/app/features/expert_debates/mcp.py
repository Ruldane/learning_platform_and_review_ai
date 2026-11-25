from app.agents.tools.expert_debate_port import EXPERT_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="expert_debates",
    actions=(
        McpAction(
            "GET /expert-debates",
            1,
            "expert_debates_list_recent",
            "Lists the account's debates.",
            untrusted=("[].question",),
        ),
        McpAction(
            "GET /expert-debates/{debate_id}",
            1,
            "expert_debates_read_thread",
            "Reads the speeches, their sources and the user's judgment.",
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
            "Asks the debate a question and launches the workflow.",
            launches="expert_debate",
            untrusted=("question",),
        ),
        McpAction(
            "PUT /expert-debates/{debate_id}/judgment",
            3,
            "expert_debates_judge_debate",
            "Records the personal judgment on the debate. Requires confirmation.",
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
