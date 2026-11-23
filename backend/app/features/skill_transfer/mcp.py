"""Un client MCP autorisé peut relire et programmer un contrôle."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_VIEW = frozenset({"id", "proof", "due_on", "available", "stage", "exercise", "assessment"})
_CONTENT = (
    "proof.label",
    "proof.skill_name",
    "exercise.title",
    "exercise.prompt",
    "assessment.feedback",
    "assessment.criteria[]",
)

MCP = FeatureMcp(
    feature="skill_transfer",
    actions=(
        McpAction(
            "GET /skill-transfers/proofs",
            1,
            "skill_transfer_list_proofs",
            "Liste les preuves de compétences du compte.",
            untrusted=("[].label", "[].skill_name"),
        ),
        McpAction(
            "GET /skill-transfers",
            1,
            "skill_transfer_list",
            "Relit le journal des contrôles de transfert.",
            response_fields=_VIEW,
            untrusted=tuple(f"[].{path}" for path in _CONTENT),
        ),
        McpAction(
            "GET /skill-transfers/{transfer_id}",
            1,
            "skill_transfer_read",
            "Relit l’exercice et, après réponse, l’appréciation.",
            response_fields=_VIEW,
            untrusted=_CONTENT,
        ),
        McpAction(
            "POST /skill-transfers",
            2,
            "skill_transfer_schedule",
            "Programme un contrôle de transfert à partir d’une preuve détenue.",
            response_fields=_VIEW,
            untrusted=_CONTENT,
        ),
        McpAction(
            "POST /skill-transfers/{transfer_id}/prepare",
            3,
            "skill_transfer_prepare_transfer",
            "Prépare le contrôle de transfert. Demande à confirmer.",
            launches="skill_transfer",
        ),
        McpAction(
            "POST /skill-transfers/{transfer_id}/answer",
            3,
            "skill_transfer_submit_transfer_answer",
            "Remet la réponse au contrôle de transfert. Demande à confirmer.",
            launches="skill_transfer",
        ),
    ),
    graphs=(McpGraph("skill_transfer", follow_only=True),),
)
