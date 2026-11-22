from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="decision_lab",
    actions=(
        McpAction(
            "POST /decision-lab/compare",
            2,
            "decision_lab_compare",
            "Compare deux architectures sous une charge et une panne simulées, sans sauvegarde.",
        ),
        McpAction(
            "GET /decision-lab/scenarios",
            1,
            "decision_lab_list_scenarios",
            "Liste les scénarios sauvegardés du compte.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /decision-lab/scenarios/{scenario_id}",
            1,
            "decision_lab_read_scenario",
            "Relit les hypothèses, les mesures et la critique d’un scénario sauvegardé.",
            untrusted=("title", "critique"),
        ),
        McpAction(
            "POST /decision-lab/scenarios",
            2,
            "decision_lab_save_scenario",
            "Sauvegarde un scénario en recalculant les mesures à partir des hypothèses.",
            untrusted=("title", "critique"),
        ),
    ),
)
