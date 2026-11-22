import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { TrialVerdict } from "./types";

const PROJECT = "/ide/sessions/{session_id}/code-trials";

export async function readTrial(
  sessionId: string,
  trialId: string | undefined,
  signal: AbortSignal,
) {
  if (trialId) {
    return unwrap(
      await api.GET("/ide/sessions/{session_id}/code-trials/{trial_id}", {
        params: { path: { session_id: sessionId, trial_id: trialId } },
        signal,
      }),
    );
  }
  return unwrap(await api.GET(PROJECT, { params: { path: { session_id: sessionId } }, signal }));
}

export async function openTrial(sessionId: string) {
  return unwrap(await api.POST(PROJECT, { params: { path: { session_id: sessionId } } }));
}

export async function saveVerdict(sessionId: string, trialId: string, body: TrialVerdict) {
  return unwrap(
    await api.PUT("/ide/sessions/{session_id}/code-trials/{trial_id}/verdict", {
      params: { path: { session_id: sessionId, trial_id: trialId } },
      body,
    }),
  );
}
