from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="decision_lab",
    actions=(
        McpAction(
            "POST /decision-lab/compare",
            2,
            "decision_lab_compare",
            "Compares two architectures under a simulated load and failure, without saving.",
        ),
        McpAction(
            "GET /decision-lab/scenarios",
            1,
            "decision_lab_list_scenarios",
            "Lists the account's saved scenarios.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /decision-lab/scenarios/{scenario_id}",
            1,
            "decision_lab_read_scenario",
            "Reads the assumptions, measurements and critique of a saved scenario.",
            untrusted=("title", "critique"),
        ),
        McpAction(
            "POST /decision-lab/scenarios",
            2,
            "decision_lab_save_scenario",
            "Saves a scenario, recomputing the measurements from the assumptions.",
            untrusted=("title", "critique"),
        ),
    ),
)
