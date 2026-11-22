from app.features.message_review.preferences import FEATURE
from app.mcp.base import FeatureMcp, McpAction

_ROOT = "/message-reviews"
_ANSWER = _ROOT + "/{challenge_id}/answer"
_CONSENT = "L'interface gère le consentement, la discussion privée et le jeton Nod associé."

MCP = FeatureMcp(
    feature=FEATURE,
    actions=(
        McpAction(
            f"POST {_ROOT}/claim",
            2,
            "message_review_claim",
            "Réserve une fiche due dans le créneau consenti. Même défi sur rejeu. Nod seul.",
            untrusted=("challenge.question",),
        ),
        McpAction(
            f"GET {_ANSWER}",
            1,
            "message_review_reveal",
            "Lit le verso du défi quand la personne de la discussion le demande. Nod seul.",
            untrusted=("answer",),
        ),
        McpAction(
            f"POST {_ANSWER}",
            2,
            "message_review_answer",
            "Relaye uniquement l'avis explicite de la personne de la discussion privée sur ce "
            "défi. Réussi : ok. À revoir : fail. Ne jamais choisir l'avis à sa place. Nod seul.",
        ),
    ),
    excluded={f"GET {_ROOT}/settings": _CONSENT, f"PUT {_ROOT}/settings": _CONSENT},
)
