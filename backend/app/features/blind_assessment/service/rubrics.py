from app.agents.tools.blind_assessment_port import BlindCriterion
from app.features.blind_assessment.schemas import BlindRubric, RubricId

RUBRICS: dict[RubricId, BlindRubric] = {
    "clarity": BlindRubric(
        id="clarity",
        title="Clarté de lecture",
        criteria=[
            BlindCriterion(
                label="Structure",
                instructions="Les sections et leur ordre guident la lecture.",
            ),
            BlindCriterion(
                label="Lisibilité",
                instructions="Les formulations sont courtes, naturelles et sans jargon inutile.",
            ),
            BlindCriterion(
                label="Précision",
                instructions="Le rôle, les actions et les résultats sont distingués.",
            ),
        ],
    ),
    "evidence": BlindRubric(
        id="evidence",
        title="Solidité des preuves",
        criteria=[
            BlindCriterion(
                label="Résultats observables",
                instructions="Les réalisations décrivent des effets qu’on peut constater.",
            ),
            BlindCriterion(
                label="Contexte des chiffres",
                instructions="Les chiffres utiles sont expliqués avec périmètre et période.",
            ),
            BlindCriterion(
                label="Rôle personnel",
                instructions="La contribution de la candidate est explicite.",
            ),
        ],
    ),
}
