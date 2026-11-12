"""Export `.ics` (D88) : un événement sur la journée par tâche, identifiant stable."""

from datetime import date

import httpx
from icalendar import Calendar

from tests.features.program.conftest import Draft
from tests.features.program.support import API, tasks_of, view


async def test_ics_has_one_all_day_event_per_task(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    r = await client.get(f"{API}/programs/{draft_program.program_id}/export.ics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert 'filename="programme.ics"' in r.headers["content-disposition"]
    cal = Calendar.from_ical(r.content)
    events = cal.walk("VEVENT")
    tasks = tasks_of(program)
    assert len(events) == len(tasks) == 12
    assert str(cal["PRODID"]) == "-//Tremplin//Programme//FR"
    assert str(cal["X-WR-CALNAME"]) == "Parcours données"
    first = next(e for e in events if str(e["SUMMARY"]) == "Lire le chapitre 1")
    task = next(t for t in tasks if t["title"] == "Lire le chapitre 1")
    assert str(first["UID"]) == f"{task['id']}@tremplin"
    start = first.decoded("DTSTART")
    assert isinstance(start, date) and start.isoformat() == task["planned_date"]
    assert b"DTSTART;VALUE=DATE:" in r.content
    description = str(first["DESCRIPTION"])
    assert "120 min" in description and "Module Bases" in description
    assert "Notes prises" in description
