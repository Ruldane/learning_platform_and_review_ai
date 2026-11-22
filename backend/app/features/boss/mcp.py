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
    ),
    graphs=(McpGraph(BOSS_GRAPH, follow_only=True),),
    excluded={
        "POST /boss/programs/{program_id}": "Démarrage du chronomètre par l’utilisatrice.",
        "POST /boss/programs/{program_id}/submit": "Remise chronométrée de l’utilisatrice.",
    },
)
