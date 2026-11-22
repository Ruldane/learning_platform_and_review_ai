"""Lecture de la projection. Tout changement reste dans le parcours de replanification."""

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
    """Compare les rythmes pour un programme validé et le relevé du poste et de la zone choisis."""
    return await forecast(db, current.id, params)
