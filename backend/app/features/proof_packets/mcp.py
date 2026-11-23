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
            "Liste les rendus de mission approuvés et leurs révisions.",
            untrusted=("[].title",),
        ),
        McpAction(
            "POST /proof-packets/preview",
            2,
            "proof_packets_preview",
            "Prévisualise les preuves sélectionnées sans sauvegarder le manifeste.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets",
            1,
            "proof_packets_list",
            "Liste les dossiers privés du compte.",
            untrusted=("[].title",),
        ),
        McpAction(
            "POST /proof-packets",
            2,
            "proof_packets_save",
            "Fige les preuves et mesures confirmées par l’empreinte de l’aperçu.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets/{packet_id}",
            1,
            "proof_packets_read",
            "Relit le manifeste privé enregistré et son empreinte.",
            untrusted=_TEXT,
        ),
        McpAction(
            "GET /proof-packets/{packet_id}/export",
            1,
            "proof_packets_get_export_file",
            "Lit les métadonnées du dossier de preuves et donne le lien local.",
            artifact=True,
            untrusted=("text",),
        ),
    ),
)
