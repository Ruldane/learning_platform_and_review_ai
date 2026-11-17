"""Déclaration MCP de `replan` : replanifier un programme et lire son historique."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="replan",
    actions=(
        McpAction(
            "POST /programs/{program_id}/replan",
            2,
            "replan_start_replan",
            "Lance une replanification (« cette semaine je n'ai que 5 heures ») : le Stratège "
            "propose, rien n'est écrit sans la réponse de January.",
        ),
        McpAction(
            "GET /programs/{program_id}/versions",
            1,
            "replan_list_versions",
            "Les versions du plan d'un programme, la plus récente d'abord.",
        ),
    ),
    graphs=(
        McpGraph(
            "replan",
            summary="Replanifie un programme (`program_id`, `trigger`, message facultatif).",
        ),
    ),
)
