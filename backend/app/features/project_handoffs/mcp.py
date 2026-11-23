from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="project_handoffs",
    actions=(
        McpAction(
            "GET /project-handoffs/source/{project_id}",
            1,
            "project_handoffs_read_source",
            "Relit le dernier rendu d’un projet privé du compte.",
            untrusted=("project_title", "description", "repo_url"),
        ),
        McpAction(
            "POST /project-handoffs/preview",
            2,
            "project_handoffs_preview",
            "Prévisualise un guide de reprise et calcule son empreinte.",
            untrusted=("markdown",),
        ),
        McpAction(
            "GET /project-handoffs",
            1,
            "project_handoffs_list",
            "Liste les guides privés approuvés du compte.",
            untrusted=("[].project_title",),
        ),
        McpAction(
            "POST /project-handoffs",
            2,
            "project_handoffs_approve",
            "Fige un guide de reprise avec l’accord explicite et l’empreinte de l’aperçu.",
            untrusted=("project_title", "markdown"),
        ),
        McpAction(
            "GET /project-handoffs/{handoff_id}",
            1,
            "project_handoffs_read",
            "Relit un guide approuvé du compte.",
            untrusted=("project_title", "markdown"),
        ),
        McpAction(
            "GET /project-handoffs/{handoff_id}/export",
            1,
            "project_handoffs_get_export_text",
            "Lit le Markdown du guide de reprise et donne son lien local.",
            artifact=True,
            untrusted=("text",),
        ),
    ),
)
