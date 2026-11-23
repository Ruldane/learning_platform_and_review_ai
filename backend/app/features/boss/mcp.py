from app.agents.tools.boss_port import BOSS_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="boss",
    actions=(
        McpAction(
            "GET /boss/programs/{program_id}",
            1,
            "boss_read_program",
            "Lit l’état et l’évaluation du Boss d’un programme.",
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
            "Démarre le chronomètre du Boss. Demande à confirmer.",
        ),
        McpAction(
            "POST /boss/programs/{program_id}/submit",
            3,
            "boss_submit_program_boss",
            "Remet le défi du Boss pour évaluation. Demande à confirmer.",
            launches="boss_review",
        ),
    ),
    graphs=(McpGraph(BOSS_GRAPH, follow_only=True),),
)
