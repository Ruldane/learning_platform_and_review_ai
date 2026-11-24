from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.incident_replay import IncidentReplay
from app.features.incident_replay.repository import IncidentReplays
from app.features.incident_replay.scenarios import SCENARIOS
from app.features.incident_replay.schemas import IncidentNote, IncidentReplayIn, IncidentScenarioOut


def catalog() -> list[IncidentScenarioOut]:
    return [summary for summary, _ in SCENARIOS.values()]


async def _require(repo: IncidentReplays, replay_id: str) -> IncidentReplay:
    row = await repo.get(replay_id)
    if row is None:
        raise AppError("incident_replay_not_found", "Replay not found.", 404)
    return row


async def history(db: AsyncSession, user_id: str) -> list[IncidentReplay]:
    return await IncidentReplays(db, user_id).recent()


async def read(db: AsyncSession, user_id: str, replay_id: str) -> IncidentReplay:
    return await _require(IncidentReplays(db, user_id), replay_id)


async def create(db: AsyncSession, user_id: str, body: IncidentReplayIn) -> IncidentReplay:
    repo = IncidentReplays(db, user_id)
    await repo.begin_write()
    receipt = str(body.receipt)
    previous = await repo.by_receipt(receipt)
    if previous is not None:
        if previous.scenario != body.scenario:
            raise AppError(
                "incident_receipt_used", "This receipt was already used for another incident.", 409
            )
        return previous
    scenario = SCENARIOS.get(body.scenario)
    if scenario is None:
        raise AppError("incident_scenario_not_found", "Practice incident not found.", 404)
    summary, events = scenario
    return await repo.add(
        receipt=receipt,
        scenario=summary.key,
        title=summary.title,
        timeline=[event.model_dump() for event in events],
    )


async def annotate(
    db: AsyncSession, user_id: str, replay_id: str, note: IncidentNote
) -> IncidentReplay:
    repo = IncidentReplays(db, user_id)
    await repo.begin_write()
    row = await _require(repo, replay_id)
    if note.step >= len(row.timeline):
        raise AppError(
            "incident_step_out_of_range", "This point in the timeline does not exist.", 422
        )
    record = note.model_dump()
    if record in row.notes:
        return row
    if len(row.notes) >= 100:
        raise AppError("incident_notes_full", "This replay already holds 100 hypotheses.", 409)
    row.notes = [*row.notes, record]
    return row
