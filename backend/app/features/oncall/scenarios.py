"""Service Python et métriques fictives, entièrement reproductibles par graine."""

from dataclasses import dataclass
from typing import Literal

ScenarioKind = Literal["latency", "queue", "quota", "fidelity"]
KINDS: tuple[ScenarioKind, ...] = ("latency", "queue", "quota", "fidelity")
MAX_MINUTE = 12
SIZES = (3, 7, 11)
REFERENCE = "routine fictive disponible"
SOURCE = "service.py"


@dataclass(frozen=True)
class Fixture:
    title: str
    setting: str
    broken: int | bool
    normal: int


FIXTURES: dict[ScenarioKind, Fixture] = {
    "latency": Fixture("Temps de réponse", "LATENCY_MS", 880, 180),
    "queue": Fixture("File de traitement", "QUEUE_CAPACITY", 2, 0),
    "quota": Fixture("Quota de traitement", "DAILY_LIMIT", 2, 0),
    "fidelity": Fixture("Fidélité d’une réponse", "USE_REFERENCE", False, 0),
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
    """Traite des données générées pour l'exercice."""
    latency = LATENCY_MS if incident_active else {_HEALTHY["LATENCY_MS"]!r}
    capacity = QUEUE_CAPACITY if incident_active else {_HEALTHY["QUEUE_CAPACITY"]!r}
    limit = DAILY_LIMIT if incident_active else {_HEALTHY["DAILY_LIMIT"]!r}
    use_reference = USE_REFERENCE if incident_active else {_HEALTHY["USE_REFERENCE"]!r}
    return {{
        "latency_ms": latency,
        "pending": max(0, requests - capacity),
        "accepted": min(requests, limit),
        "note": {REFERENCE!r} if use_reference else "information non vérifiée",
    }}


if __name__ == "__main__":
    print(serve(7, incident_active=True))
'''
    instructions = (
        "# Service d’entraînement\n\nCorrige `service.py` après avoir consulté le journal "
        "d’astreinte. Conserve `serve(requests, *, incident_active=False)` et la forme de sa "
        "réponse. Le drapeau `incident_active` rejoue les conditions de l’alerte. "
        "Le diagnostic compare la latence, la file, le quota et la fidélité au jeu de données.\n"
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
