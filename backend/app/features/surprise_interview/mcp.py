from app.features.surprise_interview.preferences import FEATURE
from app.mcp.base import FeatureMcp, McpAction

_ROOT = "/surprise-interviews"
_INVITATION = _ROOT + "/{invitation_id}"
_CONSENT = "Le consentement à l’entretien et l’association du jeton se règlent dans l’interface."

MCP = FeatureMcp(
    feature=FEATURE,
    actions=(
        McpAction(
            f"POST {_ROOT}/invite",
            2,
            "surprise_interview_invite",
            "Réserve l’invitation hebdomadaire dans la plage consentie. Nod seul.",
        ),
        McpAction(
            f"POST {_INVITATION}/accept",
            2,
            "surprise_interview_accept",
            "Lance l’entretien uniquement après l’acceptation explicite dans la discussion privée.",
            launches="interview",
        ),
        McpAction(
            f"GET {_INVITATION}",
            1,
            "surprise_interview_state",
            "Lit la question en attente ou le bilan de cet entretien. Nod seul.",
            untrusted=(
                "question.text",
                "debrief.strengths[]",
                "debrief.fixes[]",
                "debrief.improved_answer",
            ),
        ),
        McpAction(
            f"POST {_INVITATION}/answer",
            2,
            "surprise_interview_answer",
            "Relaye la réponse originale à la question indiquée et son identifiant de message. "
            "Après incident, relire l’état et renvoyer le même message si la question attend. "
            "La réponse ne peut pas être annulée. Nod seul.",
        ),
    ),
    excluded={f"GET {_ROOT}/settings": _CONSENT, f"PUT {_ROOT}/settings": _CONSENT},
)
