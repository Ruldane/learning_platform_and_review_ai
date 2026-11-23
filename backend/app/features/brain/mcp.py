"""Le bilan, les dossiers et le chat du Cerveau sont ouverts au MCP."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

SYNC = McpExclusion.BRAIN_SYNC
FOLDER_FIELDS = ("name", "path", "excluded_directories[]", "excluded_extensions[]")

MCP = FeatureMcp(
    feature="brain",
    actions=(
        McpAction("GET /brain/relay", 1, "brain_relay_status", "État du relais du Cerveau."),
        McpAction(
            "GET /brain/folders",
            1,
            "brain_list_folders",
            "Liste les dossiers et leurs exclusions.",
            untrusted=tuple(f"[].{field}" for field in FOLDER_FIELDS),
        ),
        McpAction(
            "POST /brain/folders",
            3,
            "brain_add_folder",
            "Propose de synchroniser un dossier local. Demande à confirmer.",
            side_effects="external",
            untrusted=FOLDER_FIELDS,
        ),
        McpAction(
            "PATCH /brain/folders/{folder_id}",
            3,
            "brain_change_folder",
            "Propose de modifier un dossier ou ses filtres. Demande à confirmer.",
            side_effects="external",
            untrusted=FOLDER_FIELDS,
        ),
        McpAction(
            "DELETE /brain/folders/{folder_id}",
            3,
            "brain_remove_folder",
            "Propose de retirer un dossier et ses copies synchronisées. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "GET /brain/status",
            1,
            "brain_get_status",
            "État des dossiers Cerveau sans leurs chemins.",
            untrusted=("[].name",),
        ),
        McpAction(
            "POST /brain/conversations",
            2,
            "brain_create_conversation",
            "Crée une conversation avec le Bibliothécaire.",
        ),
        McpAction(
            "GET /brain/conversation",
            1,
            "brain_read_conversation",
            "Lit une conversation du Bibliothécaire en indiquant son identifiant.",
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
            "Pose une question au Bibliothécaire dans la conversation indiquée.",
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
