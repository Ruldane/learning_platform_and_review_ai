from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.data_investigation import DataInvestigation
from app.features.data_investigation.calculate import RECIPE, metrics, results
from app.features.data_investigation.datasets import digest, source
from app.features.data_investigation.repository import Investigations
from app.features.data_investigation.schemas import (
    DatasetKey,
    InvestigationOperations,
    InvestigationOut,
    InvestigationResult,
    InvestigationRow,
    InvestigationSubmission,
    InvestigationSummary,
)

_ROWS = TypeAdapter(list[InvestigationRow])


async def require(repo: Investigations, investigation_id: str) -> DataInvestigation:
    row = await repo.get(investigation_id)
    if row is None:
        raise AppError("investigation_not_found", "Enquête introuvable.", 404)
    return row


def view(row: DataInvestigation) -> InvestigationOut:
    source_rows = _ROWS.validate_python(row.source_rows)
    operations = InvestigationOperations(operations=row.operations).operations
    current, trace = results(source_rows, tuple(operations))
    return InvestigationOut.model_validate(
        {
            "id": row.id,
            "dataset": row.dataset,
            "source_rows": source_rows,
            "source_digest": row.source_digest,
            "operations": operations,
            "trace": trace,
            "preview": metrics(current),
            "retained_rows": [item.source_row for item in current],
            "result": row.result,
            "created_at": row.created_at,
        }
    )


async def read(db: AsyncSession, user_id: str, investigation_id: str) -> InvestigationOut:
    return view(await require(Investigations(db, user_id), investigation_id))


async def create(db: AsyncSession, user_id: str, dataset: DatasetKey) -> InvestigationOut:
    repo = Investigations(db, user_id)
    scenario, rows = source(dataset)
    row = await repo.add(
        dataset=scenario.model_dump(),
        source_rows=_ROWS.dump_python(rows),
        source_digest=digest(rows),
    )
    return view(row)


async def history(db: AsyncSession, user_id: str) -> list[InvestigationSummary]:
    repo = Investigations(db, user_id)
    return [
        InvestigationSummary.model_validate(
            {
                "id": row.id,
                "title": row.dataset["title"],
                "completed": row.result is not None,
                "created_at": row.created_at,
            }
        )
        for row in await repo.recent()
    ]


def _closed() -> AppError:
    return AppError("investigation_completed", "Cette enquête est déjà remise.", 409)


async def set_operations(
    db: AsyncSession, user_id: str, investigation_id: str, plan: InvestigationOperations
) -> InvestigationOut:
    repo = Investigations(db, user_id)
    await repo.begin_write()
    row = await require(repo, investigation_id)
    if row.result is not None:
        raise _closed()
    row.operations = list(plan.operations)
    return view(row)


async def submit(
    db: AsyncSession, user_id: str, investigation_id: str, submission: InvestigationSubmission
) -> InvestigationOut:
    repo = Investigations(db, user_id)
    await repo.begin_write()
    row = await require(repo, investigation_id)
    current = view(row)
    if current.result is not None:
        if current.result.submission != submission:
            raise _closed()
        return current
    expected_rows, _ = results(current.source_rows, RECIPE)
    expected = metrics(expected_rows)
    grade = InvestigationResult(
        submission=submission,
        expected=expected,
        matches_pipeline=submission.model_dump() == current.preview.model_dump(),
        integrity_passed=set(current.operations) == set(RECIPE)
        and current.retained_rows == [item.source_row for item in expected_rows],
    )
    row.result = grade.model_dump(mode="json")
    return current.model_copy(update={"result": grade})
