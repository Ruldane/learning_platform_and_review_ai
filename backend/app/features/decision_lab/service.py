from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.decision_lab.comparison import compare as compare
from app.features.decision_lab.repository import DecisionScenarioRepository
from app.features.decision_lab.schemas import (
    DecisionScenarioCreate,
    DecisionScenarioOut,
    DecisionScenarioSummary,
)


async def save(
    db: AsyncSession, user_id: str, proposal: DecisionScenarioCreate
) -> DecisionScenarioOut:
    row = await DecisionScenarioRepository(db, user_id).add(
        title=proposal.title,
        assumptions=proposal.assumptions.model_dump(mode="json"),
        results=compare(proposal.assumptions).model_dump(mode="json"),
        critique=proposal.critique,
    )
    return DecisionScenarioOut.model_validate(row, from_attributes=True)


async def read(db: AsyncSession, user_id: str, scenario_id: str) -> DecisionScenarioOut:
    row = await DecisionScenarioRepository(db, user_id).get(scenario_id)
    if row is None:
        raise AppError("decision_scenario_not_found", "Decision scenario not found.", 404)
    return DecisionScenarioOut.model_validate(row, from_attributes=True)


async def history(db: AsyncSession, user_id: str) -> list[DecisionScenarioSummary]:
    rows = await DecisionScenarioRepository(db, user_id).history()
    return [DecisionScenarioSummary.model_validate(row, from_attributes=True) for row in rows]
