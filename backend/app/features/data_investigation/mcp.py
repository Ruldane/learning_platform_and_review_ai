from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="data_investigation",
    actions=(
        McpAction(
            "GET /data-investigations/datasets",
            1,
            "data_investigation_catalog",
            "Liste les jeux de données de formation.",
        ),
        McpAction(
            "GET /data-investigations",
            1,
            "data_investigation_list",
            "Liste les enquêtes privées du compte.",
        ),
        McpAction(
            "GET /data-investigations/{investigation_id}",
            1,
            "data_investigation_read",
            "Relit les données, opérations et résultats d’une enquête.",
        ),
        McpAction(
            "POST /data-investigations",
            2,
            "data_investigation_create",
            "Ouvre une enquête sur un jeu synthétique.",
        ),
        McpAction(
            "PATCH /data-investigations/{investigation_id}",
            2,
            "data_investigation_operations",
            "Enregistre l’ordre des opérations appliquées au jeu.",
        ),
        McpAction(
            "POST /data-investigations/{investigation_id}/submit",
            2,
            "data_investigation_submit",
            "Remet les mesures et vérifie la chaîne d’intégrité.",
        ),
    ),
)
