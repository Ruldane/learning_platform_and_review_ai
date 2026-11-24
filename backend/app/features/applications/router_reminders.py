"""Follow-ups API (SPEC 6.2, D140): the list (synced first, drafts ready to copy) and the
actions Done, Postpone 3 days, Ignore. Nothing is sent by the application. A 422 names the
fields, without values."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep
from app.features.applications.schemas import ReminderOut, ReminderPatch
from app.features.applications.service.reminders import act_on_reminder, list_reminders

router = APIRouter(prefix="/reminders", tags=["applications"], route_class=FieldPathsRoute)

_PATCH_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`reminder_not_found`"},
    409: {"description": "`reminder_closed`: the follow-up is already done or ignored"},
}


@router.get("", response_model=list[ReminderOut])
async def get_reminders(
    current: CurrentUserDep,
    rt: ApplicationsDep,
    due: Annotated[bool, Query()] = True,
) -> list[ReminderOut]:
    """The follow-ups, by ascending due date, after syncing with the records: `due=true`
    (default): pending and due today; `due=false`: all (upcoming, done, ignored)."""
    return await list_reminders(rt, current.id, due=due)


@router.patch("/{reminder_id}", response_model=ReminderOut, responses=_PATCH_ERRORS)
async def patch_reminder(
    reminder_id: Annotated[str, Path(min_length=1, max_length=36)],
    body: ReminderPatch,
    current: CurrentUserDep,
    rt: ApplicationsDep,
) -> ReminderOut:
    """`done` (the follow-up done; "Followed up" or "No response" depending on the kind),
    `postpone` (+3 days, stays pending), `ignore`."""
    return await act_on_reminder(rt, current.id, reminder_id, body.action)
