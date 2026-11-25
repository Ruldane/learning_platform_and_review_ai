"""Outils de lecture et actions explicites de la pile."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="reading_stack",
    actions=(
        McpAction(
            "GET /reading-stack",
            1,
            "reading_stack_list",
            "Lists the items in the stack.",
            untrusted=("items[].title", "items[].summary", "items[].reason", "items[].company"),
        ),
        McpAction(
            "GET /reading-stack/{item_id}",
            1,
            "reading_stack_read",
            "Shows the reading, its source and its accessible text.",
            untrusted=(
                "title",
                "summary",
                "text",
                "reason",
                "company",
                "annotations[].term",
                "annotations[].definition",
                "annotations[].chapter",
            ),
        ),
        McpAction(
            "PATCH /reading-stack/{item_id}",
            2,
            "reading_stack_mark",
            "Marks as read or unread.",
            untrusted=("title", "summary", "text", "reason", "company"),
        ),
        McpAction(
            "GET /reading-stack/sources",
            1,
            "reading_stack_list_sources",
            "Lists the sources configured for the stack.",
            untrusted=("[].label", "[].value"),
        ),
        McpAction(
            "POST /reading-stack/sources",
            2,
            "reading_stack_add_source",
            "Saves a topic, a domain or an RSS feed.",
            untrusted=("label", "value"),
        ),
        McpAction(
            "PATCH /reading-stack/sources/{source_id}",
            2,
            "reading_stack_pause_source",
            "Pauses or resumes collection from a source.",
            untrusted=("label", "value"),
        ),
        McpAction(
            "DELETE /reading-stack/sources/{source_id}",
            3,
            "reading_stack_remove_source",
            "Removes a source from collection. Needs confirmation.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/memory",
            2,
            "reading_stack_keep",
            "Keeps the item and its source in memory.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/cards",
            2,
            "reading_stack_make_cards",
            "Creates a review card from the summary or from a verified passage of the text.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/plan",
            2,
            "reading_stack_plan",
            "Proposes a reading in a validated program. The change waits for approval.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/application",
            2,
            "reading_stack_create_application",
            "Creates an internal application from a posting, with a duplicate check.",
        ),
    ),
)
