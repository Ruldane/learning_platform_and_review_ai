from app.mcp.base import FeatureMcp, McpAction

_EVIDENCE_TEXT = ("title", "finding", "expected")
_EXERCISE_TEXT = tuple(f"evidence[].{field}" for field in _EVIDENCE_TEXT)
_GROUP_TEXT = (
    "label",
    *(f"observations[].evidence.{field}" for field in _EVIDENCE_TEXT),
    *(f"exercise.{field}" for field in _EXERCISE_TEXT),
)

MCP = FeatureMcp(
    feature="error_atlas",
    actions=(
        McpAction(
            "GET /error-atlas",
            1,
            "error_atlas_list_hypotheses",
            "Relit les hypothèses de prérequis, leurs erreurs observées et les exercices choisis.",
            untrusted=tuple(f"[].{field}" for field in _GROUP_TEXT),
        ),
        McpAction(
            "GET /error-atlas/evidence",
            1,
            "error_atlas_list_evidence",
            "Liste les erreurs récentes des quiz notés et les critères non remplis des projets.",
            untrusted=tuple(f"[].{field}" for field in _EVIDENCE_TEXT),
        ),
        McpAction(
            "POST /error-atlas/observations",
            2,
            "error_atlas_record_observation",
            "Associe une erreur vérifiée à une hypothèse choisie et au degré de confiance indiqué.",
            untrusted=_GROUP_TEXT,
        ),
        McpAction(
            "POST /error-atlas/hypotheses/{hypothesis_id}/exercise",
            2,
            "error_atlas_choose_exercise",
            "Fige une fiche corrective privée avec les observations citées dans l’hypothèse.",
            untrusted=_EXERCISE_TEXT,
        ),
    ),
)
