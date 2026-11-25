"""MCP declaration for `mcp`: level 4, nothing is exposed (MCP does not manage itself)."""

from app.mcp.base import FeatureMcp, McpExclusion

MCP = FeatureMcp(
    feature="mcp",
    excluded={
        route: McpExclusion.MCP_ADMIN
        for route in (
            "GET /mcp/settings",
            "PUT /mcp/settings",
            "GET /mcp/features",
            "GET /mcp/actions",
            "POST /mcp/tokens",
            "GET /mcp/tokens",
            "DELETE /mcp/tokens/{token_id}",
            "POST /mcp/relay/pairing",
            "DELETE /mcp/relay/pairing",
            "GET /mcp/relay/status",
            "POST /mcp/relay/exchange",
            "GET /mcp/confirmations",
            "POST /mcp/confirmations/{confirmation_id}/confirm",
            "POST /mcp/confirmations/{confirmation_id}/refuse",
            "GET /mcp/calls",
            "GET /mcp/changes",
            "POST /mcp/changes/{call_id}/undo",
        )
    },
)
