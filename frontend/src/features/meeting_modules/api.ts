import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export const meetingPath = "/etudier/modules-reunion";
export const meetingsKey = ["meeting_modules"] as const;

type ModuleDraft = components["schemas"]["MeetingModuleIn"];

export async function listMeetings(signal: AbortSignal) {
  return unwrap(await api.GET("/meeting-modules", { signal }));
}

export async function prepareMeeting(body: ModuleDraft) {
  return unwrap(await api.POST("/meeting-modules", { body }));
}

export async function readMeeting(id: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/meeting-modules/{module_id}", {
      params: { path: { module_id: id } },
      signal,
    }),
  );
}

export async function setSelection(id: string, lines: number[]) {
  return unwrap(
    await api.PUT("/meeting-modules/{module_id}/selection", {
      params: { path: { module_id: id } },
      body: { lines },
    }),
  );
}

export async function publishMeeting(id: string, lines: number[]) {
  return unwrap(
    await api.POST("/meeting-modules/{module_id}/publish", {
      params: { path: { module_id: id } },
      body: { lines },
    }),
  );
}
