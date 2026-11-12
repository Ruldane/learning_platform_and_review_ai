"""Export du programme en `.ics` (SPEC 3.4, D88) : un événement sur la journée par tâche (les
tâches ont un jour, pas d'heure), identifiant stable `{task_id}@tremplin` pour qu'un nouvel
import mette à jour les événements au lieu de les doubler."""

from datetime import UTC, datetime, timedelta

from icalendar import Calendar, Event

from app.features.program.schemas import ModuleOut, ProgramOut, TaskOut

PRODID = "-//Tremplin//Programme//FR"
_TYPES = {
    "lire": "Lire",
    "regarder": "Regarder",
    "pratiquer": "Pratiquer",
    "quiz": "Quiz",
    "projet": "Projet",
}


def _description(task: TaskOut, module: ModuleOut) -> str:
    lines = [
        f"Type : {_TYPES.get(task.type, task.type)}",
        f"Durée : {task.minutes} min",
        f"Critère de fin : {task.done_criterion}",
        f"Module : {module.title}",
    ]
    if task.already_known:
        lines.append("Déjà acquis : révision")
    return "\n".join(lines)


def _event(task: TaskOut, module: ModuleOut, stamp: datetime) -> Event:
    event = Event()
    event.add("uid", f"{task.id}@tremplin")
    event.add("dtstamp", stamp)
    event.add("dtstart", task.planned_date)  # date seule : DTSTART;VALUE=DATE
    event.add("dtend", task.planned_date + timedelta(days=1))
    event.add("summary", task.title)
    event.add("description", _description(task, module))
    event.add("transp", "TRANSPARENT")  # la journée n'est pas bloquée dans l'agenda
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
