from app.agents.tools.boss_port import BOSS_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="boss",
    actions=(
        McpAction(
            "GET /boss/programs/{program_id}",
            1,
            "boss_read_program",
            "Reads the state and grading of a program's Boss.",
            untrusted=(
                "title",
                "attempt.grade.rubric.readability.feedback",
                "attempt.grade.rubric.maintenance.feedback",
            ),
        ),
        McpAction(
            "POST /boss/programs/{program_id}",
            3,
            "boss_start_program_boss",
            "Starts the Boss timer. Requires confirmation.",
        ),
        McpAction(
            "POST /boss/programs/{program_id}/submit",
            3,
            "boss_submit_program_boss",
            "Submits the Boss challenge for grading. Requires confirmation.",
            launches="boss_review",
        ),
    ),
    graphs=(McpGraph(BOSS_GRAPH, follow_only=True),),
)
