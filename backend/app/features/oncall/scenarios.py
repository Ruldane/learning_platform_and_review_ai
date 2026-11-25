"""Python service and fictitious metrics, fully reproducible from a seed."""

from dataclasses import dataclass
from typing import Literal

ScenarioKind = Literal["latency", "queue", "quota", "fidelity"]
KINDS: tuple[ScenarioKind, ...] = ("latency", "queue", "quota", "fidelity")
MAX_MINUTE = 12
SIZES = (3, 7, 11)
REFERENCE = "fictitious routine available"
SOURCE = "service.py"


@dataclass(frozen=True)
class Fixture:
    title: str
    setting: str
    broken: int | bool
    normal: int


FIXTURES: dict[ScenarioKind, Fixture] = {
    "latency": Fixture("Response time", "LATENCY_MS", 880, 180),
    "queue": Fixture("Processing queue", "QUEUE_CAPACITY", 2, 0),
    "quota": Fixture("Processing quota", "DAILY_LIMIT", 2, 0),
    "fidelity": Fixture("Response fidelity", "USE_REFERENCE", False, 0),
}
_HEALTHY: dict[str, int | bool] = {
    "LATENCY_MS": 180,
    "QUEUE_CAPACITY": 12,
    "DAILY_LIMIT": 12,
    "USE_REFERENCE": True,
}


def project_files(kind: ScenarioKind) -> dict[str, str]:
    fixture = FIXTURES[kind]
    values = {**_HEALTHY, fixture.setting: fixture.broken}
    config = "\n".join(f"{name} = {value!r}" for name, value in values.items())
    body = f'''{config}


def serve(requests, *, incident_active=False):
    """Processes data generated for the exercise."""
    latency = LATENCY_MS if incident_active else {_HEALTHY["LATENCY_MS"]!r}
    capacity = QUEUE_CAPACITY if incident_active else {_HEALTHY["QUEUE_CAPACITY"]!r}
    limit = DAILY_LIMIT if incident_active else {_HEALTHY["DAILY_LIMIT"]!r}
    use_reference = USE_REFERENCE if incident_active else {_HEALTHY["USE_REFERENCE"]!r}
    return {{
        "latency_ms": latency,
        "pending": max(0, requests - capacity),
        "accepted": min(requests, limit),
        "note": {REFERENCE!r} if use_reference else "unverified information",
    }}


if __name__ == "__main__":
    print(serve(7, incident_active=True))
'''
    instructions = (
        "# Training service\n\nFix `service.py` after reading the on-call log. "
        "Keep `serve(requests, *, incident_active=False)` and the shape of its "
        "response. The `incident_active` flag replays the alert conditions. "
        "The diagnostic compares latency, queue, quota and fidelity against the dataset.\n"
    )
    return {SOURCE: body, "README.md": instructions}


def observation(
    kind: ScenarioKind, seed: int, minute: int, alert_at: int, *, repaired: bool
) -> dict[str, object]:
    event = "alert" if minute == alert_at else "sample"
    fixture = FIXTURES[kind]
    noise = (seed + minute * 17) % 4
    if minute < alert_at or repaired:
        magnitude = fixture.normal + (noise if kind == "latency" else 0)
    elif kind == "latency":
        magnitude = int(fixture.broken) + noise
    elif kind in ("queue", "quota"):
        magnitude = SIZES[(seed + minute) % len(SIZES)] - int(fixture.broken)
    else:
        magnitude = 1
    return {"id": str(minute), "minute": minute, "kind": event, "metric": kind, "value": magnitude}
