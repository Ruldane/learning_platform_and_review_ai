from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "excerpts[].text")

MCP = FeatureMcp(
    feature="meeting_modules",
    actions=(
        McpAction(
            "GET /meeting-modules",
            1,
            "meeting_modules_list",
            "Lists the account's private drafts and modules.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /meeting-modules/{module_id}",
            1,
            "meeting_modules_read",
            "Reads a module's excerpts and sequence.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /meeting-modules",
            2,
            "meeting_modules_prepare",
            "Prepares a draft from a chosen text.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PUT /meeting-modules/{module_id}/selection",
            2,
            "meeting_modules_select",
            "Chooses the excerpts that feed the sequence.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /meeting-modules/{module_id}/publish",
            2,
            "meeting_modules_publish",
            "Saves the approved sequence as a private module.",
            untrusted=_TEXT,
        ),
    ),
)
