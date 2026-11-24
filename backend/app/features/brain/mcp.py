"""Le bilan, les dossiers et le chat du Cerveau sont ouverts au MCP."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

SYNC = McpExclusion.BRAIN_SYNC
FOLDER_FIELDS = ("name", "path", "excluded_directories[]", "excluded_extensions[]")

MCP = FeatureMcp(
    feature="brain",
    actions=(
        McpAction("GET /brain/relay", 1, "brain_relay_status", "Status of the Brain relay."),
        McpAction(
            "GET /brain/folders",
            1,
            "brain_list_folders",
            "Lists the folders and their exclusions.",
            untrusted=tuple(f"[].{field}" for field in FOLDER_FIELDS),
        ),
        McpAction(
            "POST /brain/folders",
            3,
            "brain_add_folder",
            "Proposes to sync a local folder. Needs confirmation.",
            side_effects="external",
            untrusted=FOLDER_FIELDS,
        ),
        McpAction(
            "PATCH /brain/folders/{folder_id}",
            3,
            "brain_change_folder",
            "Proposes to change a folder or its filters. Needs confirmation.",
            side_effects="external",
            untrusted=FOLDER_FIELDS,
        ),
        McpAction(
            "DELETE /brain/folders/{folder_id}",
            3,
            "brain_remove_folder",
            "Proposes to remove a folder and its synced copies. Needs confirmation.",
            side_effects="external",
        ),
        McpAction(
            "GET /brain/status",
            1,
            "brain_get_status",
            "Status of the Brain folders, without their paths.",
            untrusted=("[].name",),
        ),
        McpAction(
            "POST /brain/conversations",
            2,
            "brain_create_conversation",
            "Creates a conversation with the Librarian.",
        ),
        McpAction(
            "GET /brain/conversation",
            1,
            "brain_read_conversation",
            "Reads a Librarian conversation, given its id.",
            untrusted=(
                "turns[].question",
                "turns[].answer",
                "turns[].sources[].title",
                "turns[].sources[].excerpt",
            ),
        ),
        McpAction(
            "POST /brain/conversation/messages",
            2,
            "brain_ask_librarian",
            "Asks the Librarian a question in the given conversation.",
            launches="conversation",
        ),
    ),
    excluded={
        "POST /brain/sync-token": SYNC,
        "GET /brain/sync/folders": SYNC,
        "GET /brain/sync/folders/{folder_id}/inventory": SYNC,
        "POST /brain/sync/folders/{folder_id}/files": SYNC,
        "POST /brain/sync/folders/{folder_id}/remove": SYNC,
        "POST /brain/sync/folders/{folder_id}/report": SYNC,
    },
)
