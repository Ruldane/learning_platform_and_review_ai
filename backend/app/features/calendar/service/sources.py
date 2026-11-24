"""Re-read only the items confirmed in Tremplin, in the current account."""

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.core.errors import AppError
from app.features.applications.service.views import get_application
from app.features.calendar.schemas import Selection, StudySelection
from app.features.program.service.programs import load
from app.features.settings.service import SettingsService


@dataclass(frozen=True)
class Source:
    title: str
    day: date
    minutes: int
    zone: ZoneInfo


async def read_source(db: AsyncSession, user_id: str, selection: Selection) -> Source:
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    if isinstance(selection, StudySelection):
        loaded = await load(db, user_id, selection.program_id)
        modules = {module.id for module in loaded.modules if not module.skipped}
        for task in loaded.tasks:
            if (
                loaded.program.status == "validated"
                and task.id == selection.source_id
                and task.status == "todo"
                and task.module_id in modules
                and task.minutes > 0
            ):
                return Source(task.title, task.planned_date, task.minutes, zone)
    else:
        application = await get_application(db, user_id, selection.source_id)
        if application.interview_on and application.status == "interview":
            return Source(
                f"Interview {application.title} · {application.company}",
                application.interview_on,
                selection.minutes,
                zone,
            )
    raise AppError("calendar_source_not_found", "Study block or interview not found.", 404)
