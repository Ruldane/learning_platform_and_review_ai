from app.agents.tools.blind_assessment_port import BlindCriterion
from app.features.blind_assessment.schemas import BlindRubric, RubricId

RUBRICS: dict[RubricId, BlindRubric] = {
    "clarity": BlindRubric(
        id="clarity",
        title="Reading clarity",
        criteria=[
            BlindCriterion(
                label="Structure",
                instructions="The sections and their order guide the reader.",
            ),
            BlindCriterion(
                label="Readability",
                instructions="The wording is short, natural and free of needless jargon.",
            ),
            BlindCriterion(
                label="Precision",
                instructions="Role, actions and results are kept distinct.",
            ),
        ],
    ),
    "evidence": BlindRubric(
        id="evidence",
        title="Strength of evidence",
        criteria=[
            BlindCriterion(
                label="Observable results",
                instructions="Achievements describe effects that can be observed.",
            ),
            BlindCriterion(
                label="Context for figures",
                instructions="Useful figures are explained with their scope and period.",
            ),
            BlindCriterion(
                label="Personal role",
                instructions="The candidate's contribution is explicit.",
            ),
        ],
    ),
}
