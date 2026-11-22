"""Un client MCP autorisé peut relire et programmer un contrôle."""

from app.mcp.base import FeatureMcp, McpAction

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
    ),
    excluded={
        "POST /skill-transfers/{transfer_id}/prepare": "Préparation à la demande dans l’interface.",
        "POST /skill-transfers/{transfer_id}/answer": "Réponse personnelle de January.",
        "graph:skill_transfer": "Lancé par POST /skill-transfers/{transfer_id}/prepare ou /answer.",
    },
)
