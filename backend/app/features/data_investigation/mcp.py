from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="data_investigation",
    actions=(
        McpAction(
            "GET /data-investigations/datasets",
            1,
            "data_investigation_catalog",
            "Lists the training datasets.",
        ),
        McpAction(
            "GET /data-investigations",
            1,
            "data_investigation_list",
            "Lists the account's private investigations.",
        ),
        McpAction(
            "GET /data-investigations/{investigation_id}",
            1,
            "data_investigation_read",
            "Reads an investigation's data, operations and results.",
        ),
        McpAction(
            "POST /data-investigations",
            2,
            "data_investigation_create",
            "Opens an investigation on a synthetic dataset.",
        ),
        McpAction(
            "PATCH /data-investigations/{investigation_id}",
            2,
            "data_investigation_operations",
            "Records the order of the operations applied to the dataset.",
        ),
        McpAction(
            "POST /data-investigations/{investigation_id}/submit",
            2,
            "data_investigation_submit",
            "Submits the measurements and checks the integrity chain.",
        ),
    ),
)
