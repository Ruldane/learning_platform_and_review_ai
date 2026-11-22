from app.features.decision_lab.comparison import compare
from app.features.decision_lab.schemas import ArchitectureAssumptions, DecisionAssumptions


def assumptions(load: int = 100, duration: int = 60, outage: int = 10) -> DecisionAssumptions:
    return DecisionAssumptions(
        request_rate=load,
        duration_minutes=duration,
        outage_minutes=outage,
        architecture_a=ArchitectureAssumptions(
            replicas=1, replica_capacity_rps=100, hourly_cost_cents=10
        ),
        architecture_b=ArchitectureAssumptions(
            replicas=2, replica_capacity_rps=60, hourly_cost_cents=8
        ),
    )


def test_compares_a_shared_load_and_outage_with_integer_costs() -> None:
    scenario = assumptions()
    result = compare(scenario)
    assert result == compare(scenario)
    assert result.attempted_requests == 360_000
    assert result.architecture_a.served_requests == 300_000
    assert result.architecture_a.missed_requests == 60_000
    assert result.architecture_a.served_basis_points == 8_333
    assert result.architecture_a.cost_cents == 10
    assert result.architecture_b.served_requests == 336_000
    assert result.architecture_b.missed_requests == 24_000
    assert result.architecture_b.served_basis_points == 9_333
    assert result.architecture_b.cost_cents == 16


def test_zero_load_and_full_outage_are_defined() -> None:
    zero = compare(assumptions(load=0, duration=3, outage=0))
    assert zero.attempted_requests == zero.architecture_a.missed_requests == 0
    assert zero.architecture_a.served_basis_points is None
    assert zero.architecture_a.cost_cents == 1
    assert zero.architecture_b.cost_cents == 1

    full = compare(assumptions(duration=5, outage=5))
    assert full.architecture_a.served_requests == 0
    assert full.architecture_a.missed_requests == 30_000
    assert full.architecture_a.served_basis_points == 0
    assert full.architecture_b.served_requests == 18_000


def test_healthy_capacity_is_capped_for_an_overloaded_architecture() -> None:
    result = compare(assumptions(load=150, duration=5, outage=0))
    assert result.attempted_requests == 45_000
    assert result.architecture_a.served_requests == 30_000
    assert result.architecture_b.served_requests == 36_000
