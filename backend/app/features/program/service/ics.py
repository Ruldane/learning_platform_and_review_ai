"""Export of the program as `.ics` (SPEC 3.4, D88): one all-day event per task (tasks have a day,
not a time), stable identifier `{task_id}@tremplin` so that a new import updates the events
instead of duplicating them."""

from datetime import UTC, datetime, timedelta

from icalendar import Calendar, Event

from app.features.program.schemas import ModuleOut, ProgramOut, TaskOut

PRODID = "-//Tremplin//Program//EN"
TASK_TYPE_LABELS = {
    "read": "Read",
    "watch": "Watch",
    "practice": "Practice",
    "quiz": "Quiz",
    "project": "Project",
}


def _description(task: TaskOut, module: ModuleOut) -> str:
    lines = [
        f"Type: {TASK_TYPE_LABELS[task.type]}",
        f"Duration: {task.minutes} min",
        f"Completion criterion: {task.done_criterion}",
        f"Module: {module.title}",
    ]
    if task.already_known:
        lines.append("Review (already known)")
    return "\n".join(lines)


def _event(task: TaskOut, module: ModuleOut, stamp: datetime) -> Event:
    event = Event()
    event.add("uid", f"{task.id}@tremplin")
    event.add("dtstamp", stamp)
    event.add("dtstart", task.planned_date)  # date only: DTSTART;VALUE=DATE
    event.add("dtend", task.planned_date + timedelta(days=1))
    event.add("summary", task.title)
    event.add("description", _description(task, module))
    event.add("transp", "TRANSPARENT")  # the day is not blocked in the calendar
    return event


def program_ics(program: ProgramOut) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", PRODID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", program.title)
    stamp = datetime.now(UTC)
    for week in program.weeks:
        for module in week.modules:
            for task in module.tasks:
                calendar.add_component(_event(task, module, stamp))
    body: bytes = calendar.to_ical()
    return body
