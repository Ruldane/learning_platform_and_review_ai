from hashlib import sha256

from pydantic import TypeAdapter

from app.features.data_investigation.schemas import (
    DatasetKey,
    InvestigationDataset,
    InvestigationRow,
)

_DELIVERIES = InvestigationDataset(
    key="deliveries-v1",
    title="Checking a festival's deliveries",
    brief=(
        "Compute the number of completed deliveries and the number of kits handed over. "
        "A single shipment can be corrected or cancelled by its latest revision."
    ),
)
_SUPPLIES = InvestigationDataset(
    key="supplies-v1",
    title="Receiving a workshop's equipment",
    brief=(
        "Compute the number of completed deliveries and the number of workstations received. "
        "Rows without a reference and invalid quantities are not evidence."
    ),
)

_ROWS = TypeAdapter(list[InvestigationRow])


def source(key: DatasetKey) -> tuple[InvestigationDataset, list[InvestigationRow]]:
    match key:
        case "deliveries-v1":
            spec = _DELIVERIES
            data = [
                ("F-01", 1, "delivered", 10),
                ("F-02", 1, "delivered", 6),
                ("F-03", 1, "delivered", -2),
                ("F-01", 2, "delivered", 12),
                ("F-04", 1, "delivered", 3),
                ("", 1, "delivered", 6),
                ("F-02", 2, "cancelled", 6),
                ("F-05", 1, "pending", 4),
                ("F-06", 1, "delivered", 7),
            ]
        case "supplies-v1":
            spec = _SUPPLIES
            data = [
                ("A-01", 1, "pending", 5),
                ("A-02", 1, "delivered", 11),
                ("A-03", 1, "delivered", -5),
                ("A-01", 2, "delivered", 5),
                ("", 1, "delivered", 3),
                ("A-04", 1, "delivered", 8),
                ("A-04", 2, "cancelled", 8),
                ("A-05", 1, "delivered", 4),
            ]
    return spec, _ROWS.validate_python(
        [
            {
                "source_row": index,
                "reference": ref,
                "revision": rev,
                "status": status,
                "units": units,
            }
            for index, (ref, rev, status, units) in enumerate(data, start=1)
        ]
    )


def catalog() -> list[InvestigationDataset]:
    return [_DELIVERIES, _SUPPLIES]


def digest(rows: list[InvestigationRow]) -> str:
    return sha256(_ROWS.dump_json(rows)).hexdigest()
