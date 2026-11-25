from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("lesson_title", "source_markdown", "review_markdown", "reading_steps[]")

MCP = FeatureMcp(
    feature="lesson_variants",
    actions=(
        McpAction(
            "GET /lesson-variants",
            1,
            "lesson_variants_list",
            "Lists the account's private editions and their source revisions.",
            untrusted=("[].lesson_title",),
        ),
        McpAction(
            "POST /lesson-variants",
            2,
            "lesson_variants_prepare",
            "Saves two readings of the published version of one of the account's lessons.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /lesson-variants/{edition_id}",
            1,
            "lesson_variants_read",
            "Reads the private variants and the stored source version.",
            untrusted=_TEXT,
        ),
    ),
)
