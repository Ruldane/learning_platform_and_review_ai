from app.features.data_investigation.schemas import (
    InvestigationMetrics,
    InvestigationRow,
    InvestigationStep,
    Operation,
)

RECIPE: tuple[Operation, ...] = (
    "latest_revision",
    "delivered_only",
    "declared_identifier",
    "positive_units",
)


def _latest(rows: list[InvestigationRow]) -> list[InvestigationRow]:
    latest: dict[str, InvestigationRow] = {}
    for row in sorted(rows, key=lambda item: (item.revision, item.source_row)):
        if row.reference:
            latest[row.reference] = row
    return [row for row in rows if not row.reference or latest[row.reference] == row]


def _apply(rows: list[InvestigationRow], operation: Operation) -> list[InvestigationRow]:
    match operation:
        case "latest_revision":
            return _latest(rows)
        case "delivered_only":
            return [row for row in rows if row.status == "delivered"]
        case "declared_identifier":
            return [row for row in rows if row.reference.strip()]
        case "positive_units":
            return [row for row in rows if row.units > 0]


def results(
    source: list[InvestigationRow], operations: tuple[Operation, ...]
) -> tuple[list[InvestigationRow], list[InvestigationStep]]:
    current = source
    trace = []
    for operation in operations:
        previous = current
        current = _apply(current, operation)
        remaining = {row.source_row for row in current}
        trace.append(
            InvestigationStep(
                operation=operation,
                removed_rows=[
                    row.source_row for row in previous if row.source_row not in remaining
                ],
                remaining_rows=len(current),
            )
        )
    return current, trace


def metrics(rows: list[InvestigationRow]) -> InvestigationMetrics:
    return InvestigationMetrics(units=sum(row.units for row in rows), deliveries=len(rows))
