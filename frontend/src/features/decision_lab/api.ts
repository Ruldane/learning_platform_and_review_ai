import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { Assumptions, Scenario } from "./types";

export async function compare(assumptions: Assumptions) {
  return unwrap(await api.POST("/decision-lab/compare", { body: assumptions }));
}

export async function save(scenario: Scenario) {
  return unwrap(await api.POST("/decision-lab/scenarios", { body: scenario }));
}

export async function listScenarios(signal: AbortSignal) {
  return unwrap(await api.GET("/decision-lab/scenarios", { signal }));
}

export async function readScenario(id: string) {
  return unwrap(await api.GET("/decision-lab/scenarios/{scenario_id}", {
    params: { path: { scenario_id: id } },
  }));
}
