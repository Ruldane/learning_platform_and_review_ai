import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { Activity, ScenarioKind } from "./types";

export async function listIncidents(signal?: AbortSignal) {
  return unwrap(await api.GET("/oncall/incidents", { signal }));
}

export async function incidentView(id: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/oncall/incidents/{incident_id}", {
      params: { path: { incident_id: id } },
      signal,
    }),
  );
}

export async function createIncident(kind: ScenarioKind | null) {
  return unwrap(await api.POST("/oncall/incidents", { body: { kind, seed: null } }));
}

export async function runActivity(id: string, event: Activity): Promise<void> {
  const params = { path: { incident_id: id } };
  switch (event.kind) {
    case "advance":
      unwrap(await api.POST("/oncall/incidents/{incident_id}/advance", { params }));
      return;
    case "observe":
      unwrap(
        await api.POST("/oncall/incidents/{incident_id}/events/{event_id}/observe", {
          params: { path: { ...params.path, event_id: event.eventId } },
        }),
      );
      return;
    case "diagnostic":
      unwrap(await api.POST("/oncall/incidents/{incident_id}/diagnostic", { params }));
      return;
    case "report":
      unwrap(
        await api.POST("/oncall/incidents/{incident_id}/report", {
          params,
          body: { text: event.text },
        }),
      );
  }
}
