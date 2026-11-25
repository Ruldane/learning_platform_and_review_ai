import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export const investigationsPath = "/study/investigations";
export const investigationsKey = ["data_investigations"] as const;

type CaseKey = components["schemas"]["InvestigationCreate"]["dataset"];
type Operations = components["schemas"]["InvestigationOperations"]["operations"];
type Submission = components["schemas"]["InvestigationSubmission"];

export async function readLibrary(signal: AbortSignal) {
  const [cases, history] = await Promise.all([
    api.GET("/data-investigations/datasets", { signal }),
    api.GET("/data-investigations", { signal }),
  ]);
  return { cases: unwrap(cases), history: unwrap(history) };
}

export async function createInvestigation(dataset: CaseKey) {
  return unwrap(await api.POST("/data-investigations", { body: { dataset } }));
}

export async function readInvestigation(id: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/data-investigations/{investigation_id}", {
      params: { path: { investigation_id: id } },
      signal,
    }),
  );
}

export async function updateOperations(id: string, operations: Operations) {
  return unwrap(
    await api.PATCH("/data-investigations/{investigation_id}", {
      params: { path: { investigation_id: id } },
      body: { operations },
    }),
  );
}

export async function submitInvestigation(id: string, body: Submission) {
  return unwrap(
    await api.POST("/data-investigations/{investigation_id}/submit", {
      params: { path: { investigation_id: id } },
      body,
    }),
  );
}
