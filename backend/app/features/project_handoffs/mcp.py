from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="project_handoffs",
    actions=(
        McpAction(
            "GET /project-handoffs/source/{project_id}",
            1,
            "project_handoffs_read_source",
            "Reads the latest submission of one of the account's private projects.",
            untrusted=("project_title", "description", "repo_url"),
        ),
        McpAction(
            "POST /project-handoffs/preview",
            2,
            "project_handoffs_preview",
            "Previews a handoff guide and computes its fingerprint.",
            untrusted=("markdown",),
        ),
        McpAction(
            "GET /project-handoffs",
            1,
            "project_handoffs_list",
            "Lists the account's approved private guides.",
            untrusted=("[].project_title",),
        ),
        McpAction(
            "POST /project-handoffs",
            2,
            "project_handoffs_approve",
            "Freezes a handoff guide with explicit approval and the preview's fingerprint.",
            untrusted=("project_title", "markdown"),
        ),
        McpAction(
            "GET /project-handoffs/{handoff_id}",
            1,
            "project_handoffs_read",
            "Reads one of the account's approved guides.",
            untrusted=("project_title", "markdown"),
        ),
        McpAction(
            "GET /project-handoffs/{handoff_id}/export",
            1,
            "project_handoffs_get_export_text",
            "Reads the handoff guide's Markdown and gives its local link.",
            artifact=True,
            untrusted=("text",),
        ),
    ),
)
