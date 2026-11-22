"""Charge constante, sans file d’attente, pendant une panne d’une réplique."""

from app.features.decision_lab.schemas import (
    ArchitectureAssumptions,
    DecisionAssumptions,
    DecisionComparison,
    DecisionMetrics,
)

_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60
_BASIS_POINTS = 10_000


def _round_ratio(numerator: int, denominator: int) -> int:
    """Arrondit le quotient positif à l’entier le plus proche, au-dessus à mi-chemin."""
    return (numerator + denominator // 2) // denominator


def _metrics(
    scenario: DecisionAssumptions, architecture: ArchitectureAssumptions, attempted: int
) -> DecisionMetrics:
    healthy_rps = architecture.replicas * architecture.replica_capacity_rps
    degraded_rps = healthy_rps - architecture.replica_capacity_rps
    normal_minutes = scenario.duration_minutes - scenario.outage_minutes
    served = _SECONDS_PER_MINUTE * (
        normal_minutes * min(scenario.request_rate, healthy_rps)
        + scenario.outage_minutes * min(scenario.request_rate, degraded_rps)
    )
    billed = architecture.hourly_cost_cents * architecture.replicas * scenario.duration_minutes
    return DecisionMetrics(
        served_requests=served,
        missed_requests=attempted - served,
        served_basis_points=_round_ratio(served * _BASIS_POINTS, attempted) if attempted else None,
        cost_cents=_round_ratio(billed, _MINUTES_PER_HOUR),
    )


def compare(scenario: DecisionAssumptions) -> DecisionComparison:
    attempted = scenario.request_rate * scenario.duration_minutes * _SECONDS_PER_MINUTE
    return DecisionComparison(
        attempted_requests=attempted,
        architecture_a=_metrics(scenario, scenario.architecture_a, attempted),
        architecture_b=_metrics(scenario, scenario.architecture_b, attempted),
    )
