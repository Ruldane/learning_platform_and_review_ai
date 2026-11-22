from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.decision_lab import service
from app.features.decision_lab.schemas import (
    DecisionAssumptions,
    DecisionComparison,
    DecisionScenarioCreate,
    DecisionScenarioOut,
    DecisionScenarioSummary,
)

router = APIRouter(prefix="/decision-lab", tags=["decision_lab"], route_class=FieldPathsRoute)


@router.post("/compare")
async def compare(body: DecisionAssumptions, user: CurrentUserDep) -> DecisionComparison:
    return service.compare(body)


@router.post("/scenarios", status_code=201)
async def save_scenario(
    body: DecisionScenarioCreate, db: Db, user: CurrentUserDep
) -> DecisionScenarioOut:
    return await service.save(db, user.id, body)


@router.get("/scenarios")
async def list_scenarios(db: Db, user: CurrentUserDep) -> list[DecisionScenarioSummary]:
    return await service.history(db, user.id)


@router.get("/scenarios/{scenario_id}")
async def read_scenario(scenario_id: UUID, db: Db, user: CurrentUserDep) -> DecisionScenarioOut:
    return await service.read(db, user.id, str(scenario_id))
