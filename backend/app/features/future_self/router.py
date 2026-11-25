"""Reading of the projection. Any change stays in the replanning flow."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.future_self.schemas import FutureSelfOut, FutureSelfQuery
from app.features.future_self.service import forecast

router = APIRouter(prefix="/future-self", tags=["future_self"], route_class=FieldPathsRoute)


@router.get("", response_model=FutureSelfOut)
async def get_projection(
    current: CurrentUserDep, db: Db, params: Annotated[FutureSelfQuery, Query()]
) -> FutureSelfOut:
    """Compares paces for a validated program and the survey of the chosen role and area."""
    return await forecast(db, current.id, params)
