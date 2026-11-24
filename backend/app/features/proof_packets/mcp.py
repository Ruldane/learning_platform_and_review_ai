from app.mcp.base import FeatureMcp, McpAction

_TEXT = (
    "manifest.title",
    "manifest.proofs[].title",
    "manifest.proofs[].artifact",
    "manifest.proofs[].measurements[].label",
)

MCP = FeatureMcp(
    feature="proof_packets",
    actions=(
        McpAction(
            "GET /proof-packets/sources",
            1,
            "proof_packets_list_sources",
            "Lists the approved mission submissions and their revisions.",
            untrusted=("[].title",),
        ),
        McpAction(
            "POST /proof-packets/preview",
            2,
            "proof_packets_preview",
            "Previews the selected proofs without saving the manifest.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets",
            1,
            "proof_packets_list",
            "Lists the account's private proof packets.",
            untrusted=("[].title",),
        ),
        McpAction(
            "POST /proof-packets",
            2,
            "proof_packets_save",
            "Freezes the proofs and measurements confirmed by the preview's fingerprint.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets/{packet_id}",
            1,
            "proof_packets_read",
            "Reads the saved private manifest and its fingerprint.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets/{packet_id}/export",
            1,
            "proof_packets_get_export_file",
            "Reads the proof packet's metadata and gives the local link.",
            artifact=True,
            untrusted=("text",),
        ),
    ),
)
