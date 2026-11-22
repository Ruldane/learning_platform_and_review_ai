import type {
  ArchitectureFieldsValue, ArchitectureMeasures, AssumptionFields, ComparisonView, ScenarioLink,
} from "./components/viewTypes";
import type { Architecture, Assumptions, Comparison, ScenarioSummary } from "./types";

function architectureIn(fields: ArchitectureFieldsValue): Architecture {
  return {
    replicas: fields.replicas,
    replica_capacity_rps: fields.capacityPerReplica,
    hourly_cost_cents: fields.hourlyCents,
  };
}

function architectureOut(architecture: Architecture): ArchitectureFieldsValue {
  return {
    replicas: architecture.replicas,
    capacityPerReplica: architecture.replica_capacity_rps,
    hourlyCents: architecture.hourly_cost_cents,
  };
}

export function assumptionsIn(fields: AssumptionFields): Assumptions {
  return {
    request_rate: fields.rate,
    duration_minutes: fields.duration,
    outage_minutes: fields.outage,
    architecture_a: architectureIn(fields.first),
    architecture_b: architectureIn(fields.second),
  };
}

export function assumptionsOut(assumptions: Assumptions): AssumptionFields {
  return {
    rate: assumptions.request_rate,
    duration: assumptions.duration_minutes,
    outage: assumptions.outage_minutes,
    first: architectureOut(assumptions.architecture_a),
    second: architectureOut(assumptions.architecture_b),
  };
}

function measures(value: Comparison["architecture_a"]): ArchitectureMeasures {
  return {
    served: value.served_requests,
    missed: value.missed_requests,
    servedFraction: value.served_basis_points === null ? null : value.served_basis_points / 10_000,
    costEuros: value.cost_cents / 100,
  };
}

export function comparisonOut(value: Comparison): ComparisonView {
  return {
    attempted: value.attempted_requests,
    first: measures(value.architecture_a),
    second: measures(value.architecture_b),
  };
}

export function historyOut(items: ScenarioSummary[]): ScenarioLink[] {
  return items.map(({ id, title, created_at }) => ({ id, title, createdAt: created_at }));
}
