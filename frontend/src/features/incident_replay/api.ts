import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export const replayBasePath = "/etudier/replay-incident";
export const replayKey = ["incident_replay"] as const;

type StartReplay = components["schemas"]["IncidentReplayIn"];
type IncidentNote = components["schemas"]["IncidentNote"];

export async function openLibrary(signal: AbortSignal) {
  const [catalog, history] = await Promise.all([
    api.GET("/incident-replays/scenarios", { signal }),
    api.GET("/incident-replays", { signal }),
  ]);
  return { scenarios: unwrap(catalog), history: unwrap(history) };
}

export async function startReplay(body: StartReplay) {
  return unwrap(await api.POST("/incident-replays", { body }));
}

export async function readReplay(replayId: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/incident-replays/{replay_id}", {
      signal,
      params: { path: { replay_id: replayId } },
    }),
  );
}

export async function saveNote(replayId: string, body: IncidentNote) {
  return unwrap(
    await api.POST("/incident-replays/{replay_id}/notes", {
      body,
      params: { path: { replay_id: replayId } },
    }),
  );
}
