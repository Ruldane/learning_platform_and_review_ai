import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Selection =
  components["schemas"]["StudySelection"] | components["schemas"]["InterviewSelection"];
export type Proposal = components["schemas"]["CalendarProposalOut"];

export async function getConnection(signal?: AbortSignal) {
  return unwrap(await api.GET("/calendar/connection", { signal }));
}

export async function connect() {
  return unwrap(await api.POST("/calendar/connection", { body: { consent: true } }));
}

export async function disconnect() {
  return unwrap(await api.DELETE("/calendar/connection"));
}

export async function propose(body: Selection) {
  return unwrap(await api.POST("/calendar/proposals", { body }));
}

export async function confirm(id: string) {
  return unwrap(
    await api.POST("/calendar/proposals/{proposal_id}/confirm", {
      params: { path: { proposal_id: id } },
    }),
  );
}

export async function getPrograms(signal?: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

export async function getProgram(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}", {
      params: { path: { program_id: programId } },
      signal,
    }),
  );
}

export async function getApplications(signal?: AbortSignal) {
  return unwrap(await api.GET("/applications", { signal }));
}
