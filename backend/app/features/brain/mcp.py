"""Le bilan et le chat du Cerveau sont ouverts au MCP."""

from app.mcp.base import FeatureMcp, McpAction

INTERFACE = "Configuration des dossiers réservée au compte connecté dans l'interface."
SYNC = "Canal du relais réservé au jeton de synchronisation, hors MCP."

MCP = FeatureMcp(
    feature="brain",
    actions=(
        McpAction(
            "GET /brain/status",
            1,
            "brain_get_status",
            "État des dossiers Cerveau sans leurs chemins.",
            untrusted=("[].name",),
        ),
        McpAction(
            "GET /brain/conversation",
            1,
            "brain_read_conversation",
            "Lit le fil du Bibliothécaire.",
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
            "Pose une question au Bibliothécaire sur les notes synchronisées et les leçons.",
            launches="conversation",
        ),
    ),
    excluded={
        "GET /brain/folders": INTERFACE,
        "POST /brain/folders": INTERFACE,
        "PATCH /brain/folders/{folder_id}": INTERFACE,
        "DELETE /brain/folders/{folder_id}": INTERFACE,
        "POST /brain/sync-token": INTERFACE,
        "GET /brain/sync/folders": SYNC,
        "GET /brain/sync/folders/{folder_id}/inventory": SYNC,
        "POST /brain/sync/folders/{folder_id}/files": SYNC,
        "POST /brain/sync/folders/{folder_id}/remove": SYNC,
        "POST /brain/sync/folders/{folder_id}/report": SYNC,
    },
)
