from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "excerpts[].text")

MCP = FeatureMcp(
    feature="meeting_modules",
    actions=(
        McpAction(
            "GET /meeting-modules",
            1,
            "meeting_modules_list",
            "Liste les brouillons et modules privés du compte.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /meeting-modules/{module_id}",
            1,
            "meeting_modules_read",
            "Relit les extraits et la séquence d’un module.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /meeting-modules",
            2,
            "meeting_modules_prepare",
            "Prépare un brouillon à partir d’un texte choisi.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PUT /meeting-modules/{module_id}/selection",
            2,
            "meeting_modules_select",
            "Choisit les extraits qui alimentent la séquence.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /meeting-modules/{module_id}/publish",
            2,
            "meeting_modules_publish",
            "Range la séquence approuvée comme module privé.",
            untrusted=_TEXT,
        ),
    ),
)
