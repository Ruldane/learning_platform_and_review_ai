from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.data_investigation import service
from app.features.data_investigation.datasets import catalog
from app.features.data_investigation.schemas import (
    InvestigationCreate,
    InvestigationDataset,
    InvestigationOperations,
    InvestigationOut,
    InvestigationSubmission,
    InvestigationSummary,
)

router = APIRouter(
    prefix="/data-investigations", tags=["data_investigation"], route_class=FieldPathsRoute
)


@router.get("/datasets")
async def list_datasets(user: CurrentUserDep) -> list[InvestigationDataset]:
    return catalog()


@router.get("")
async def list_investigations(db: Db, user: CurrentUserDep) -> list[InvestigationSummary]:
    return await service.history(db, user.id)


@router.post("", status_code=201)
async def create_investigation(
    body: InvestigationCreate, db: Db, user: CurrentUserDep
) -> InvestigationOut:
    return await service.create(db, user.id, body.dataset)


@router.get("/{investigation_id}")
async def read_investigation(
    investigation_id: UUID, db: Db, user: CurrentUserDep
) -> InvestigationOut:
    return await service.read(db, user.id, str(investigation_id))


@router.patch("/{investigation_id}")
async def apply_operations(
    investigation_id: UUID, body: InvestigationOperations, db: Db, user: CurrentUserDep
) -> InvestigationOut:
    return await service.set_operations(db, user.id, str(investigation_id), body)


@router.post("/{investigation_id}/submit")
async def submit_investigation(
    investigation_id: UUID, body: InvestigationSubmission, db: Db, user: CurrentUserDep
) -> InvestigationOut:
    return await service.submit(db, user.id, str(investigation_id), body)
