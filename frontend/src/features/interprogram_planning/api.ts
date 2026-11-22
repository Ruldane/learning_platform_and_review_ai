import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Week = components["schemas"]["SharedWeekOut"];
export type ProgramOption = components["schemas"]["SharedWeekOption"];

export const sharedWeeksKey = ["interprogram-planning"] as const;

export async function getOptions(signal?: AbortSignal) {
  return unwrap(await api.GET("/interprogram-planning/options", { signal }));
}

export async function getWeeks(signal?: AbortSignal) {
  return unwrap(await api.GET("/interprogram-planning", { signal }));
}

export async function prepareWeek(weekStart: string, programIds: string[]) {
  return unwrap(
    await api.POST("/interprogram-planning", {
      body: { week_start: weekStart, program_ids: programIds },
    }),
  );
}

export async function applyWeek(id: string) {
  return unwrap(
    await api.POST("/interprogram-planning/{proposal_id}/accept", {
      body: { confirmed: true },
      params: { path: { proposal_id: id } },
    }),
  );
}
